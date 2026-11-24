"""TMDB-backed movie and television catalogue."""

import json
import logging
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from pathlib import Path

from PyQt6.QtCore import QThread, Qt, QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices, QPixmap
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)
from PyQt6.QtSvgWidgets import QSvgWidget


LOGGER = logging.getLogger(__name__)
TMDB_API_ROOT = "https://api.themoviedb.org/3"
TMDB_IMAGE_ROOT = "https://image.tmdb.org/t/p/w342"


class CatalogSearchWorker(QThread):
    completed = pyqtSignal(int, list, str)

    def __init__(
        self,
        request_id: int,
        media_type: str,
        query: str,
        api_key: str,
        parent=None,
    ):
        super().__init__(parent)
        self.request_id = request_id
        self.media_type = media_type
        self.query = query
        self.api_key = api_key

    def run(self):
        parameters = urlencode(
            {
                "api_key": self.api_key,
                "query": self.query,
                "include_adult": "false",
                "language": "en-US",
                "page": 1,
            }
        )
        request = Request(
            f"{TMDB_API_ROOT}/search/{self.media_type}?{parameters}",
            headers={"Accept": "application/json", "User-Agent": "PrismMediaHub/1.0"},
        )
        try:
            with urlopen(request, timeout=15) as response:
                payload = json.loads(response.read().decode("utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("TMDB returned an unexpected results format.")
            results = payload.get("results", [])
            if not isinstance(results, list):
                raise ValueError("TMDB returned an unexpected results format.")
            valid_results = [item for item in results if isinstance(item, dict)]
            self.completed.emit(self.request_id, valid_results[:20], "")
        except HTTPError as error:
            if error.code == 401:
                message = "TMDB rejected the API key. Check TMDB_API_KEY in your .env file."
            elif error.code == 429:
                message = "TMDB search is temporarily rate-limited. Try again shortly."
            else:
                message = f"TMDB could not complete the search (HTTP {error.code})."
            self.completed.emit(self.request_id, [], message)
        except (URLError, TimeoutError, OSError):
            LOGGER.exception("TMDB catalogue request failed")
            self.completed.emit(
                self.request_id,
                [],
                "Could not reach TMDB. Check your internet connection and try again.",
            )
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
            LOGGER.exception("TMDB returned an invalid catalogue response")
            self.completed.emit(
                self.request_id,
                [],
                "TMDB returned data Prism could not read. Try again later.",
            )


class MovieCatalogView(QWidget):
    def __init__(self, api_key: str, parent=None):
        super().__init__(parent)
        self.api_key = api_key
        self.search_request_id = 0
        self.search_worker: CatalogSearchWorker | None = None
        self.current_results: list[dict] = []
        self.current_media_type = "movie"
        self.selected_result: dict | None = None
        self.poster_reply = None
        self._build_ui()
        self._network_manager = QNetworkAccessManager(self)

    def _build_ui(self):
        self.setObjectName("movie_catalog")
        self.setStyleSheet("""
            QWidget#movie_catalog {
                background-color: #0F0F12;
                color: #FFFFFF;
                font-family: "Segoe UI";
            }
            QLabel {
                color: #FFFFFF;
            }
            QLabel#body_copy,
            QLabel#result_hint,
            QLabel#details_meta {
                color: #B7B7C7;
                font-size: 12px;
            }
            QLabel#catalog_state {
                color: #B7B7C7;
                font-size: 13px;
            }
            QLabel#details_title {
                color: #FFFFFF;
                font-size: 21px;
                font-weight: 700;
            }
            QLabel#poster {
                background-color: #1A1A24;
                border: 1px solid #2E2E3E;
                border-radius: 6px;
                color: #B7B7C7;
                font-size: 11px;
            }
            QComboBox,
            QLineEdit#catalog_query {
                background-color: #1A1A24;
                border: 1px solid #3A3A49;
                border-radius: 6px;
                color: #FFFFFF;
                min-height: 38px;
                padding: 0 10px;
                font-size: 13px;
            }
            QComboBox:focus,
            QLineEdit#catalog_query:focus {
                border: 2px solid #00D2FF;
            }
            QComboBox QAbstractItemView {
                background-color: #1A1A24;
                color: #FFFFFF;
                selection-background-color: #24343A;
            }
            QPushButton {
                background-color: #1A1A24;
                border: 1px solid #454554;
                border-radius: 6px;
                color: #FFFFFF;
                min-height: 36px;
                padding: 0 12px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover:enabled {
                border-color: #00D2FF;
                background-color: #22222C;
            }
            QPushButton:focus {
                border: 2px solid #00D2FF;
            }
            QPushButton:disabled {
                color: #B7B7C7;
                border-color: #343440;
            }
            QPushButton#search_button {
                background-color: #00D2FF;
                border-color: #00D2FF;
                color: #0F0F12;
                min-width: 90px;
            }
            QPushButton#search_button:hover:enabled {
                background-color: #39DFFF;
                border-color: #39DFFF;
            }
            QTableWidget#catalog_results {
                background-color: #121216;
                alternate-background-color: #18181F;
                color: #FFFFFF;
                gridline-color: #2E2E3E;
                border: 1px solid #2E2E3E;
                selection-background-color: #24343A;
                selection-color: #FFFFFF;
            }
            QTableWidget#catalog_results::item {
                padding: 7px;
                border-bottom: 1px solid #24242D;
            }
            QHeaderView::section {
                background-color: #1A1A24;
                color: #D0D0DC;
                border: none;
                border-bottom: 1px solid #343440;
                font-weight: 650;
                padding: 8px;
            }
            QTableWidget#catalog_results:focus {
                border: 2px solid #00D2FF;
            }
            QTextBrowser#overview {
                background: transparent;
                border: none;
                color: #D1D1DC;
                font-size: 13px;
            }
            QTextBrowser#overview:focus {
                border: 1px solid #00D2FF;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(12)

        intro = QLabel("Search films or series, then open a title’s details or reference page.")
        intro.setObjectName("body_copy")
        intro.setWordWrap(True)
        layout.addWidget(intro)

        search_row = QHBoxLayout()
        search_row.setSpacing(8)
        self.media_type_combo = QComboBox()
        self.media_type_combo.addItem("Movies", "movie")
        self.media_type_combo.addItem("TV shows", "tv")
        self.media_type_combo.setAccessibleName("Catalog type")
        self.media_type_combo.setMinimumWidth(118)
        search_row.addWidget(self.media_type_combo)

        self.query_input = QLineEdit()
        self.query_input.setObjectName("catalog_query")
        self.query_input.setPlaceholderText("Search by title")
        self.query_input.setAccessibleName("Movie or TV show title")
        self.query_input.returnPressed.connect(self.search)
        search_row.addWidget(self.query_input, stretch=1)

        self.search_button = QPushButton("Search")
        self.search_button.setObjectName("search_button")
        self.search_button.clicked.connect(self.search)
        search_row.addWidget(self.search_button)
        layout.addLayout(search_row)

        content = QHBoxLayout()
        content.setSpacing(14)

        results_panel = QWidget()
        results_layout = QVBoxLayout(results_panel)
        results_layout.setContentsMargins(0, 0, 0, 0)
        results_layout.setSpacing(7)
        self.result_hint = QLabel("Choose Movies or TV shows, enter a title, then search.")
        self.result_hint.setObjectName("result_hint")
        self.result_hint.setWordWrap(True)
        results_layout.addWidget(self.result_hint)

        self.results_table = QTableWidget()
        self.results_table.setObjectName("catalog_results")
        self.results_table.setColumnCount(2)
        self.results_table.setHorizontalHeaderLabels(["Title", "Year"])
        self.results_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        self.results_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents
        )
        self.results_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.results_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.results_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.results_table.setAlternatingRowColors(True)
        self.results_table.verticalHeader().hide()
        self.results_table.itemSelectionChanged.connect(self._show_selected_result)
        self.results_table.hide()
        results_layout.addWidget(self.results_table, stretch=1)
        content.addWidget(results_panel, stretch=3)

        details_panel = QFrame()
        details_panel.setObjectName("details_panel")
        details_panel.setStyleSheet(
            "#details_panel { background-color: #141419; border: 1px solid #2E2E3E; border-radius: 7px; }"
        )
        details_panel_layout = QVBoxLayout(details_panel)
        details_panel_layout.setContentsMargins(0, 0, 0, 0)
        details_panel_layout.setSpacing(0)

        details_scroll = QScrollArea()
        details_scroll.setObjectName("details_scroll")
        details_scroll.setWidgetResizable(True)
        details_scroll.setFrameShape(QFrame.Shape.NoFrame)
        details_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        details_content = QWidget()
        details_content.setObjectName("details_content")
        details_content.setStyleSheet("background-color: #141419;")
        details_layout = QVBoxLayout(details_content)
        details_layout.setContentsMargins(14, 14, 14, 14)
        details_layout.setSpacing(9)

        self.poster_label = QLabel("Select a title")
        self.poster_label.setObjectName("poster")
        self.poster_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.poster_label.setFixedSize(126, 188)
        details_layout.addWidget(
            self.poster_label, alignment=Qt.AlignmentFlag.AlignHCenter
        )

        self.details_title = QLabel("Title details")
        self.details_title.setObjectName("details_title")
        self.details_title.setWordWrap(True)
        details_layout.addWidget(self.details_title)

        self.details_meta = QLabel("")
        self.details_meta.setObjectName("details_meta")
        self.details_meta.setWordWrap(True)
        details_layout.addWidget(self.details_meta)

        self.overview = QTextBrowser()
        self.overview.setObjectName("overview")
        self.overview.setOpenExternalLinks(False)
        self.overview.setAccessibleName("Selected title overview")
        self.overview.setPlaceholderText("A title’s overview will appear here.")
        self.overview.setText("Select a result to see its overview.")
        details_layout.addWidget(self.overview, stretch=1)

        self.tmdb_button = QPushButton("Open TMDB page")
        self.tmdb_button.setEnabled(False)
        self.tmdb_button.clicked.connect(self._open_tmdb_page)
        details_layout.addWidget(self.tmdb_button)

        self.wikipedia_button = QPushButton("Search Wikipedia")
        self.wikipedia_button.setEnabled(False)
        self.wikipedia_button.clicked.connect(self._open_wikipedia_search)
        details_layout.addWidget(self.wikipedia_button)
        details_scroll.setWidget(details_content)
        details_panel_layout.addWidget(details_scroll)
        content.addWidget(details_panel, stretch=2)
        layout.addLayout(content, stretch=1)

        credits_row = QHBoxLayout()
        logo_path = Path(__file__).resolve().parents[1] / "assets" / "tmdb" / "tmdb-logo.svg"
        self.tmdb_logo = QSvgWidget(str(logo_path))
        self.tmdb_logo.setAccessibleName("The Movie Database logo")
        self.tmdb_logo.setFixedSize(134, 58)
        credits_row.addWidget(self.tmdb_logo)
        credits_row.addStretch(1)
        self.credits_button = QPushButton("Credits")
        self.credits_button.clicked.connect(self._show_credits)
        credits_row.addWidget(self.credits_button)
        layout.addLayout(credits_row)

    def search(self):
        query = self.query_input.text().strip()
        if not query:
            self._show_state("Enter a title to search the catalogue.")
            self.query_input.setFocus()
            return
        if not self.api_key:
            self._show_state(
                "TMDB_API_KEY is missing. Add your TMDB API key to the local .env file."
            )
            return
        if self.search_worker is not None and self.search_worker.isRunning():
            return

        self.search_request_id += 1
        request_id = self.search_request_id
        self.current_media_type = self.media_type_combo.currentData()
        self.search_button.setEnabled(False)
        self.search_button.setText("Searching…")
        self.media_type_combo.setEnabled(False)
        self._show_state("Searching TMDB…")

        worker = CatalogSearchWorker(
            request_id,
            self.current_media_type,
            query,
            self.api_key,
            self,
        )
        worker.completed.connect(self._handle_search_complete)
        worker.finished.connect(self._handle_worker_finished)
        self.search_worker = worker
        worker.start()

    def _handle_search_complete(self, request_id: int, results: list, error: str):
        if request_id != self.search_request_id:
            return
        self.search_button.setEnabled(True)
        self.search_button.setText("Search")
        self.media_type_combo.setEnabled(True)
        if error:
            self._show_state(error)
            return
        if not results:
            self._show_state("No matching titles found. Try another search.")
            return

        self.current_results = results
        self.results_table.setRowCount(len(results))
        for row, item in enumerate(results):
            title = self._title_for(item, self.current_media_type)
            date = self._date_for(item, self.current_media_type)
            year = date[:4] if len(date) >= 4 else "Unknown"
            title_item = QTableWidgetItem(title)
            title_item.setData(Qt.ItemDataRole.UserRole, row)
            year_item = QTableWidgetItem(year)
            year_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.results_table.setItem(row, 0, title_item)
            self.results_table.setItem(row, 1, year_item)

        self.result_hint.setText(f"{len(results)} results")
        self.result_hint.show()
        self.results_table.show()
        self.results_table.selectRow(0)

    def _handle_worker_finished(self):
        worker = self.sender()
        if worker is self.search_worker:
            self.search_worker = None
        if worker:
            worker.deleteLater()

    def _show_state(self, message: str):
        self.results_table.clearContents()
        self.results_table.setRowCount(0)
        self.results_table.hide()
        self.current_results = []
        self.selected_result = None
        self.result_hint.setText(message)
        self.result_hint.show()
        self._reset_details()

    def _show_selected_result(self):
        selected_items = self.results_table.selectedItems()
        if not selected_items:
            return
        row = selected_items[0].row()
        if row >= len(self.current_results):
            return

        item = self.current_results[row]
        self.selected_result = item
        media_type = self.current_media_type
        title = self._title_for(item, media_type)
        date = self._date_for(item, media_type)
        year = date[:4] if len(date) >= 4 else "Year unavailable"
        rating = item.get("vote_average")
        rating_text = f"TMDB rating {rating:.1f}/10" if isinstance(rating, (int, float)) and rating else ""
        self.details_title.setText(title)
        self.details_meta.setText("  ·  ".join(value for value in (year, rating_text) if value))
        overview = str(item.get("overview") or "").strip()
        self.overview.setText(overview or "No overview is available for this title.")
        self.tmdb_button.setEnabled(True)
        self.wikipedia_button.setEnabled(True)
        self._load_poster(item.get("poster_path"))

    def _load_poster(self, poster_path):
        if self.poster_reply:
            self.poster_reply.abort()
            self.poster_reply = None
        self.poster_label.setPixmap(QPixmap())
        self.poster_label.setText("Poster\nnot available")
        if not isinstance(poster_path, str) or not poster_path.startswith("/"):
            return

        request = QNetworkRequest(QUrl(f"{TMDB_IMAGE_ROOT}{poster_path}"))
        request.setTransferTimeout(12_000)
        reply = self._network_manager.get(request)
        self.poster_reply = reply
        reply.finished.connect(lambda current_reply=reply: self._finish_poster_load(current_reply))

    def _finish_poster_load(self, reply):
        if reply is not self.poster_reply:
            reply.deleteLater()
            return
        self.poster_reply = None
        if reply.error() == QNetworkReply.NetworkError.NoError:
            pixmap = QPixmap()
            if pixmap.loadFromData(reply.readAll()):
                self.poster_label.setPixmap(
                    pixmap.scaled(
                        self.poster_label.size(),
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )
                self.poster_label.setText("")
        reply.deleteLater()

    def _reset_details(self):
        if self.poster_reply:
            reply = self.poster_reply
            self.poster_reply = None
            reply.abort()
        self.poster_label.setPixmap(QPixmap())
        self.poster_label.setText("Select a title")
        self.details_title.setText("Title details")
        self.details_meta.clear()
        self.overview.setText("Select a result to see its overview.")
        self.tmdb_button.setEnabled(False)
        self.wikipedia_button.setEnabled(False)

    def _open_tmdb_page(self):
        item = self.selected_result
        if not item:
            return
        try:
            title_id = int(item["id"])
        except (KeyError, TypeError, ValueError):
            return
        if title_id < 1:
            return
        media_type = self.current_media_type
        QDesktopServices.openUrl(
            QUrl(f"https://www.themoviedb.org/{media_type}/{title_id}")
        )

    def _open_wikipedia_search(self):
        if not self.selected_result:
            return
        title = self._title_for(self.selected_result, self.current_media_type)
        query = urlencode({"search": title})
        QDesktopServices.openUrl(QUrl(f"https://en.wikipedia.org/w/index.php?{query}"))

    def _show_credits(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Prism catalogue credits")
        dialog.setMinimumWidth(420)
        dialog.setStyleSheet("""
            QDialog {
                background-color: #0F0F12;
                color: #FFFFFF;
                font-family: "Segoe UI";
            }
            QLabel {
                color: #FFFFFF;
                font-size: 13px;
            }
            QPushButton {
                background-color: #1A1A24;
                border: 1px solid #454554;
                border-radius: 6px;
                color: #FFFFFF;
                min-height: 34px;
                padding: 0 14px;
            }
            QPushButton:focus {
                border: 2px solid #00D2FF;
            }
        """)
        layout = QVBoxLayout(dialog)
        logo = QSvgWidget(str(Path(__file__).resolve().parents[1] / "assets" / "tmdb" / "tmdb-logo.svg"))
        logo.setFixedSize(160, 70)
        layout.addWidget(logo)
        attribution = QLabel(
            "This product uses the TMDB API but is not endorsed or certified by TMDB."
        )
        attribution.setWordWrap(True)
        layout.addWidget(attribution)
        source = QPushButton("TMDB logo and attribution guidance")
        source.clicked.connect(
            lambda: QDesktopServices.openUrl(
                QUrl("https://www.themoviedb.org/about/logos-attribution")
            )
        )
        layout.addWidget(source)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(dialog.reject)
        buttons.accepted.connect(dialog.accept)
        layout.addWidget(buttons)
        dialog.exec()

    @staticmethod
    def _title_for(item: dict, media_type: str) -> str:
        key = "title" if media_type == "movie" else "name"
        return str(item.get(key) or "Untitled")

    @staticmethod
    def _date_for(item: dict, media_type: str) -> str:
        key = "release_date" if media_type == "movie" else "first_air_date"
        return str(item.get(key) or "")
