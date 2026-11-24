"""Internet Archive feature-film browser."""

import re
from html import unescape
from html.parser import HTMLParser

from PyQt6.QtCore import QThread, Qt, QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QFrame,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from ui.archive_api import (
    ArchiveAPIError,
    ArchiveMovie,
    ArchiveSearchResult,
    fetch_archive_movie,
    license_allows_playback,
    license_name,
    search_archive_movies,
)


class ArchiveSearchWorker(QThread):
    completed = pyqtSignal(int, list, str)

    def __init__(self, request_id: int, query: str, parent=None):
        super().__init__(parent)
        self.request_id = request_id
        self.query = query

    def run(self):
        try:
            results = search_archive_movies(self.query)
        except ArchiveAPIError as error:
            self.completed.emit(self.request_id, [], str(error))
            return
        self.completed.emit(self.request_id, results, "")


class ArchiveItemWorker(QThread):
    completed = pyqtSignal(int, object, str)

    def __init__(self, request_id: int, identifier: str, parent=None):
        super().__init__(parent)
        self.request_id = request_id
        self.identifier = identifier

    def run(self):
        try:
            movie = fetch_archive_movie(self.identifier)
        except ArchiveAPIError as error:
            self.completed.emit(self.request_id, None, str(error))
            return
        self.completed.emit(self.request_id, movie, "")


class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str):
        self.parts.append(data)


def _plain_description(value: str) -> str:
    parser = _TextExtractor()
    parser.feed(value)
    return re.sub(r"\s+", " ", unescape(" ".join(parser.parts))).strip()


class ArchiveCatalogView(QWidget):
    play_requested = pyqtSignal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.search_request_id = 0
        self.detail_request_id = 0
        self.search_worker: ArchiveSearchWorker | None = None
        self.workers: list[QThread] = []
        self.current_results: list[ArchiveSearchResult] = []
        self.selected_result: ArchiveSearchResult | None = None
        self.selected_movie: ArchiveMovie | None = None
        self._build_ui()

    def _build_ui(self):
        self.setObjectName("archive_catalog")
        self.setStyleSheet("""
            QWidget#archive_catalog {
                background-color: #0F0F12;
                color: #FFFFFF;
                font-family: "Segoe UI";
            }
            QLabel {
                color: #FFFFFF;
            }
            QLabel#archive_copy,
            QLabel#archive_state,
            QLabel#archive_meta {
                color: #B7B7C7;
                font-size: 12px;
            }
            QLabel#archive_title {
                color: #FFFFFF;
                font-size: 20px;
                font-weight: 700;
            }
            QLineEdit#archive_query {
                background-color: #1A1A24;
                border: 1px solid #3A3A49;
                border-radius: 6px;
                color: #FFFFFF;
                min-height: 38px;
                padding: 0 10px;
                font-size: 13px;
            }
            QLineEdit#archive_query:focus {
                border: 2px solid #00D2FF;
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
            QPushButton#archive_search {
                background-color: #00D2FF;
                border-color: #00D2FF;
                color: #0F0F12;
            }
            QTableWidget#archive_results {
                background-color: #121216;
                alternate-background-color: #18181F;
                color: #FFFFFF;
                gridline-color: #2E2E3E;
                border: 1px solid #2E2E3E;
                selection-background-color: #24343A;
                selection-color: #FFFFFF;
            }
            QHeaderView::section {
                background-color: #1A1A24;
                color: #D0D0DC;
                border: none;
                border-bottom: 1px solid #343440;
                font-weight: 650;
                padding: 8px;
            }
            QTableWidget#archive_results:focus {
                border: 2px solid #00D2FF;
            }
            QTextBrowser#archive_description {
                background: transparent;
                border: none;
                color: #D1D1DC;
                font-size: 13px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(12)

        intro = QLabel(
            "Search feature films in Internet Archive. Rights information comes "
            "from each item record and is supplied by its uploader."
        )
        intro.setObjectName("archive_copy")
        intro.setWordWrap(True)
        layout.addWidget(intro)

        search_row = QHBoxLayout()
        self.query_input = QLineEdit()
        self.query_input.setObjectName("archive_query")
        self.query_input.setPlaceholderText("Search film titles")
        self.query_input.setAccessibleName("Internet Archive film title")
        self.query_input.returnPressed.connect(self.search)
        search_row.addWidget(self.query_input, stretch=1)

        self.search_button = QPushButton("Search Archive")
        self.search_button.setObjectName("archive_search")
        self.search_button.clicked.connect(self.search)
        search_row.addWidget(self.search_button)
        layout.addLayout(search_row)

        content = QHBoxLayout()
        content.setSpacing(14)

        results_panel = QWidget()
        results_layout = QVBoxLayout(results_panel)
        results_layout.setContentsMargins(0, 0, 0, 0)
        results_layout.setSpacing(7)
        self.result_hint = QLabel("Enter a title to search feature films.")
        self.result_hint.setObjectName("archive_state")
        self.result_hint.setWordWrap(True)
        results_layout.addWidget(self.result_hint)

        self.results_table = QTableWidget()
        self.results_table.setObjectName("archive_results")
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
        self.results_table.setSelectionMode(
            QTableWidget.SelectionMode.SingleSelection
        )
        self.results_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.results_table.setAlternatingRowColors(True)
        self.results_table.verticalHeader().hide()
        self.results_table.itemSelectionChanged.connect(self._show_selected_result)
        self.results_table.hide()
        results_layout.addWidget(self.results_table, stretch=1)
        content.addWidget(results_panel, stretch=3)

        details_panel = QFrame()
        details_panel.setObjectName("archive_details")
        details_panel.setStyleSheet(
            "#archive_details { background-color: #141419; border: 1px solid #2E2E3E; border-radius: 7px; }"
        )
        details_layout = QVBoxLayout(details_panel)
        details_layout.setContentsMargins(14, 14, 14, 14)
        details_layout.setSpacing(9)

        self.details_title = QLabel("Select a film")
        self.details_title.setObjectName("archive_title")
        self.details_title.setWordWrap(True)
        details_layout.addWidget(self.details_title)

        self.details_meta = QLabel("")
        self.details_meta.setObjectName("archive_meta")
        self.details_meta.setWordWrap(True)
        self.details_meta.setTextFormat(Qt.TextFormat.PlainText)
        details_layout.addWidget(self.details_meta)

        self.description = QTextBrowser()
        self.description.setObjectName("archive_description")
        self.description.setAccessibleName("Internet Archive item description")
        self.description.setOpenExternalLinks(False)
        self.description.setPlainText("Film details will appear here.")
        details_layout.addWidget(self.description, stretch=1)

        self.play_button = QPushButton("Play in Prism")
        self.play_button.setEnabled(False)
        self.play_button.clicked.connect(self._play_selected)
        details_layout.addWidget(self.play_button)

        self.archive_button = QPushButton("Open Archive record")
        self.archive_button.setEnabled(False)
        self.archive_button.clicked.connect(self._open_archive_record)
        details_layout.addWidget(self.archive_button)
        content.addWidget(details_panel, stretch=2)
        layout.addLayout(content, stretch=1)

        rights_note = QLabel(
            "Playback is enabled only when the item lists a supported public-domain "
            "or Creative Commons license. Check the original item record before use."
        )
        rights_note.setObjectName("archive_copy")
        rights_note.setWordWrap(True)
        layout.addWidget(rights_note)

    def search(self):
        query = self.query_input.text().strip()
        if not query:
            self._show_state("Enter a film title to search Internet Archive.")
            self.query_input.setFocus()
            return
        if self.search_worker is not None and self.search_worker.isRunning():
            return

        self.search_request_id += 1
        request_id = self.search_request_id
        self.search_button.setEnabled(False)
        self.search_button.setText("Searching…")
        self._show_state("Searching Internet Archive feature films…")

        worker = ArchiveSearchWorker(request_id, query, self)
        worker.completed.connect(self._handle_search_complete)
        worker.finished.connect(lambda current=worker: self._finish_worker(current))
        self.search_worker = worker
        self.workers.append(worker)
        worker.start()

    def _handle_search_complete(
        self,
        request_id: int,
        results: list[ArchiveSearchResult],
        error: str,
    ):
        if request_id != self.search_request_id:
            return
        self.search_button.setEnabled(True)
        self.search_button.setText("Search Archive")
        if error:
            self._show_state(error)
            return
        if not results:
            self._show_state("No matching licensed feature films were found.")
            return

        self.current_results = results
        self.results_table.setRowCount(len(results))
        for row, movie in enumerate(results):
            title_item = QTableWidgetItem(movie.title)
            title_item.setData(Qt.ItemDataRole.UserRole, row)
            self.results_table.setItem(row, 0, title_item)
            year_item = QTableWidgetItem(movie.year or "Unknown")
            year_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.results_table.setItem(row, 1, year_item)

        self.result_hint.setText(f"{len(results)} results")
        self.result_hint.show()
        self.results_table.show()
        self.results_table.selectRow(0)

    def _show_state(self, message: str):
        self.detail_request_id += 1
        self.results_table.clearContents()
        self.results_table.setRowCount(0)
        self.results_table.hide()
        self.current_results = []
        self.selected_result = None
        self.selected_movie = None
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

        result = self.current_results[row]
        self.selected_result = result
        self.selected_movie = None
        self.detail_request_id += 1
        request_id = self.detail_request_id
        self.details_title.setText(result.title)
        self.details_meta.setText(
            "  ·  ".join(
                value
                for value in (
                    result.year,
                    license_name(result.license_url),
                )
                if value
            )
        )
        self.description.setPlainText(
            _plain_description(result.description) or "No description is available."
        )
        self.play_button.setEnabled(False)
        self.play_button.setText("Checking video…")
        self.archive_button.setEnabled(True)

        worker = ArchiveItemWorker(request_id, result.identifier, self)
        worker.completed.connect(self._handle_item_complete)
        worker.finished.connect(lambda current=worker: self._finish_worker(current))
        self.workers.append(worker)
        worker.start()

    def _handle_item_complete(
        self,
        request_id: int,
        movie: ArchiveMovie | None,
        error: str,
    ):
        if request_id != self.detail_request_id:
            return
        if error or movie is None:
            self.play_button.setEnabled(False)
            self.play_button.setText("Video unavailable")
            self.details_meta.setText(error or "Could not load item details.")
            return

        self.selected_movie = movie
        self.details_title.setText(movie.title)
        rights = license_name(movie.license_url)
        self.details_meta.setText("  ·  ".join(value for value in (movie.year, rights) if value))
        self.description.setPlainText(
            _plain_description(movie.description) or "No description is available."
        )
        self.archive_button.setEnabled(True)
        if not license_allows_playback(movie.license_url):
            self.play_button.setText("License not supported")
            self.play_button.setEnabled(False)
        elif not movie.stream_url:
            self.play_button.setText("No supported MP4")
            self.play_button.setEnabled(False)
        else:
            self.play_button.setText("Play in Prism")
            self.play_button.setEnabled(True)

    def _play_selected(self):
        movie = self.selected_movie
        if movie is None or movie.stream_url is None:
            return
        if not license_allows_playback(movie.license_url):
            return
        self.play_requested.emit(movie.stream_url, movie.title)

    def _open_archive_record(self):
        result = self.selected_result
        if result is None:
            return
        movie = self.selected_movie
        archive_url = movie.archive_url if movie else (
            f"https://archive.org/details/{result.identifier}"
        )
        QDesktopServices.openUrl(QUrl(archive_url))

    def _reset_details(self):
        self.details_title.setText("Select a film")
        self.details_meta.clear()
        self.description.setPlainText("Film details will appear here.")
        self.play_button.setText("Play in Prism")
        self.play_button.setEnabled(False)
        self.archive_button.setEnabled(False)

    def _finish_worker(self, worker: QThread):
        if worker in self.workers:
            self.workers.remove(worker)
        if worker is self.search_worker:
            self.search_worker = None
        worker.deleteLater()

    def closeEvent(self, event):
        for worker in self.workers:
            if worker.isRunning():
                worker.wait()
        super().closeEvent(event)
