"""Prism media hub window and destination views."""

import logging
import html
import sqlite3
from pathlib import Path

from PyQt6.QtCore import (
    QEvent,
    QThread,
    QTimer,
    Qt,
    pyqtSignal,
    pyqtSlot,
)
from PyQt6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from PyQt6.QtGui import QColor, QContextMenuEvent, QPalette

from player import AudioPlayer
from config import JAMENDO_CLIENT_ID
from ui.arcade_view import ArcadeView
from ui.music_queue import PlaybackQueue
from ui.playlist_cache import (
    add_local_playlist_track,
    delete_local_playlist_tracks,
    fetch_local_playlist_tracks,
    remove_local_playlist_track,
)
from ui.music_sources import JAMENDO_GENRES
from ui.music_workers import (
    AudioDownloadWorker,
    DatabaseWorker,
    JamendoSearchWorker,
    LocalFolderScanWorker,
)
from ui.player_bar import PlayerBar
from ui.queue_dialog import QueueDialog
from ui.sidebar import Sidebar
from ui.view_view import ViewView
import db


LOGGER = logging.getLogger(__name__)


class MusicLibraryLoader(QThread):
    loaded = pyqtSignal(int, list)
    failed = pyqtSignal(int, str)

    def __init__(self, request_id: int, user_id: str, liked_only: bool):
        super().__init__()
        self.request_id = request_id
        self.user_id = user_id
        self.liked_only = liked_only

    def run(self):
        try:
            if self.liked_only:
                songs = db.fetch_liked_songs(self.user_id)
            else:
                songs = db.fetch_all_songs()
            self.loaded.emit(self.request_id, songs)
        except Exception as error:
            LOGGER.exception("Could not load the Prism music library")
            if getattr(error, "code", None) == "PGRST205":
                message = (
                    "The Supabase music tables are missing. Run "
                    "supabase/migrations/202611060001_legacy_music_library.sql "
                    "in the Supabase SQL Editor, then add tracks to the songs table. "
                    "Jamendo and Local files work without these tables."
                )
            else:
                message = (
                    "Couldn't load the Supabase music library. Check your connection "
                    f"and permissions, then try again. Details: {error}"
                )
            self.failed.emit(self.request_id, message)


class MainWindow(QMainWindow):
    def __init__(self, user_id: str):
        super().__init__()
        self.user_id = user_id
        self.player = AudioPlayer()
        self.playback_queue = PlaybackQueue()
        self.all_songs: list[dict] = []
        self.current_songs: list[dict] = []
        self.displayed_songs: list[dict] = []
        self.playlists: dict[str, dict] = {}
        self.active_playlist_id: str | None = None
        self.music_loaded = False
        self.showing_liked_songs = False
        self.music_loader: MusicLibraryLoader | None = None
        self._background_workers: dict[int, QThread] = {}
        self.load_request_id = 0
        self.jamendo_worker: JamendoSearchWorker | None = None
        self.local_scan_worker: LocalFolderScanWorker | None = None
        self.audio_download_workers: dict[int, AudioDownloadWorker] = {}
        self.database_workers: dict[int, DatabaseWorker] = {}
        self.database_requests: dict[int, tuple] = {}
        self.database_request_id = 0
        self._queue_transition_pending = False
        self._queue_completion_handled = False
        self.queue_dialog: QueueDialog | None = None
        self.jamendo_request_id = 0
        self.local_scan_request_id = 0
        self.audio_request_id = 0
        self.local_music_folder = ""
        self.jamendo_loaded = False

        self.init_ui()
        self.playback_timer = QTimer(self)
        self.playback_timer.setInterval(250)
        self.playback_timer.timeout.connect(self._update_playback_timeline)
        self.playback_timer.start()
        self._request_playlists()

    def init_ui(self):
        self.setWindowTitle("Prism | Media Hub")
        self.resize(1160, 760)
        self.setMinimumSize(900, 620)
        self.setStyleSheet("""
            QMainWindow, QWidget#main_content {
                background-color: #0F0F12;
                color: #FFFFFF;
                font-family: "Segoe UI";
            }
            QLabel {
                color: #FFFFFF;
            }
            QLabel#eyebrow {
                color: #00D2FF;
                font-size: 11px;
                font-weight: 700;
            }
            QLabel#page_title {
                font-size: 28px;
                font-weight: 700;
            }
            QLabel#body_copy {
                color: #B7B7C7;
                font-size: 13px;
            }
            QPushButton#route_music,
            QPushButton#route_media {
                background-color: #1A1A24;
                border: 1px solid #343440;
                border-left: 3px solid #454554;
                border-radius: 7px;
                color: #FFFFFF;
                text-align: left;
                padding: 18px 20px;
                font-size: 15px;
                font-weight: 650;
            }
            QPushButton#route_music {
                border-left: 4px solid #00D2FF;
                min-height: 84px;
                font-size: 16px;
            }
            QPushButton#route_media {
                min-height: 56px;
                color: #E5E5EC;
                font-size: 14px;
            }
            QPushButton#route_music:hover,
            QPushButton#route_media:hover {
                background-color: #22222C;
                border-color: #00D2FF;
            }
            QPushButton#route_music:focus,
            QPushButton#route_media:focus,
            QPushButton#home_button:focus,
            QPushButton#retry_button:focus {
                border: 2px solid #FFFFFF;
            }
            QLineEdit#song_search {
                background-color: #1A1A24;
                border: 1px solid #3A3A49;
                border-radius: 6px;
                padding: 10px 12px;
                color: #FFFFFF;
                font-size: 13px;
            }
            QLineEdit#song_search:focus {
                border: 2px solid #00D2FF;
            }
            QComboBox#music_source,
            QComboBox#music_genre {
                background-color: #1A1A24;
                border: 1px solid #3A3A49;
                border-radius: 6px;
                color: #FFFFFF;
                min-height: 38px;
                padding: 0 10px;
            }
            QComboBox#music_source:focus,
            QComboBox#music_genre:focus {
                border: 2px solid #00D2FF;
            }
            QComboBox QAbstractItemView {
                background-color: #1A1A24;
                color: #FFFFFF;
                selection-background-color: #24343A;
                selection-color: #FFFFFF;
            }
            QPushButton#music_action {
                background-color: #1A1A24;
                border: 1px solid #454554;
                border-radius: 6px;
                color: #FFFFFF;
                min-height: 38px;
                padding: 0 12px;
            }
            QPushButton#music_action:hover {
                border-color: #00D2FF;
            }
            QPushButton#music_action:focus {
                border: 2px solid #FFFFFF;
            }
            QLabel#track_attribution {
                color: #B7B7C7;
                font-size: 11px;
            }
            QTableWidget#song_table {
                background-color: #121216;
                alternate-background-color: #18181F;
                color: #FFFFFF;
                gridline-color: #2E2E3E;
                border: 1px solid #2E2E3E;
                selection-background-color: #24343A;
                selection-color: #FFFFFF;
            }
            QTableWidget#song_table::item {
                padding: 7px;
                border-bottom: 1px solid #24242D;
            }
            QHeaderView::section {
                background-color: #1A1A24;
                color: #D0D0DC;
                border: none;
                border-bottom: 1px solid #343440;
                font-weight: 650;
                padding: 9px;
            }
            QTableWidget#song_table:focus {
                border: 2px solid #00D2FF;
            }
            QPushButton#retry_button,
            QPushButton#home_button {
                background-color: #1A1A24;
                border: 1px solid #454554;
                border-radius: 6px;
                color: #FFFFFF;
                min-height: 38px;
                padding: 0 14px;
            }
            QPushButton#retry_button:hover,
            QPushButton#home_button:hover {
                border-color: #00D2FF;
            }
        """)

        root = QWidget()
        root.setObjectName("main_content")
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        body = QHBoxLayout()
        body.setSpacing(0)

        self.sidebar = Sidebar()
        self.sidebar.navigation_changed.connect(self.handle_navigation)
        self.sidebar.playlist_created.connect(self.handle_create_playlist)
        self.sidebar.playlist_selected.connect(self.handle_playlist_selected)
        self.sidebar.playlist_renamed.connect(self.handle_rename_playlist)
        self.sidebar.playlist_deleted.connect(self.handle_delete_playlist)
        self.sidebar.playlists_refresh_requested.connect(self._request_playlists)
        body.addWidget(self.sidebar)

        self.pages = QStackedWidget()
        self.pages.addWidget(self._build_home_page())
        self.pages.addWidget(self._build_music_page())
        self.pages.addWidget(ViewView())
        self.arcade_view = ArcadeView()
        self.pages.addWidget(self.arcade_view)
        for page_index in range(self.pages.count()):
            page = self.pages.widget(page_index)
            page.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
            page.setAutoFillBackground(True)
            page_palette = page.palette()
            page_palette.setColor(QPalette.ColorRole.Window, QColor("#0F0F12"))
            page.setPalette(page_palette)
        body.addWidget(self.pages, stretch=1)
        root_layout.addLayout(body, stretch=1)

        self.player_bar = PlayerBar()
        self.player_bar.play_toggled.connect(self.handle_play_toggle)
        self.player_bar.previous_requested.connect(self.handle_previous_track)
        self.player_bar.next_requested.connect(self.handle_next_track)
        self.player_bar.queue_requested.connect(self.handle_show_queue)
        self.player_bar.shuffle_toggled.connect(self.handle_shuffle_toggled)
        self.player_bar.repeat_cycle_requested.connect(self.handle_repeat_cycle)
        self.player_bar.seek_requested.connect(self.handle_seek)
        self.player_bar.volume_changed.connect(self.player.set_volume)
        root_layout.addWidget(self.player_bar)

        self.setCentralWidget(root)
        self.sidebar.set_active("home")

    def _build_home_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(38, 34, 38, 28)
        layout.setSpacing(12)

        eyebrow = QLabel("PRISM  /  HOME")
        eyebrow.setObjectName("eyebrow")
        layout.addWidget(eyebrow)

        title = QLabel("Your next listen, watch, or round starts here.")
        title.setObjectName("page_title")
        title.setWordWrap(True)
        layout.addWidget(title)

        description = QLabel(
            "Browse music, search movies and TV, or play Snake."
        )
        description.setObjectName("body_copy")
        layout.addWidget(description)
        layout.addSpacing(15)

        music_button = QPushButton("Music & Audio\nOpen your song library and playlists")
        music_button.setObjectName("route_music")
        music_button.setAccessibleName("Open Music and Audio")
        music_button.clicked.connect(lambda: self.handle_navigation("music"))
        layout.addWidget(music_button)

        movies_button = QPushButton("Movies & TV\nSearch titles or play a local video")
        movies_button.setObjectName("route_media")
        movies_button.setAccessibleName("Open Movies and TV")
        movies_button.clicked.connect(lambda: self.handle_navigation("movies"))
        layout.addWidget(movies_button)

        arcade_button = QPushButton("Arcade\nPlay Snake or Tetris inside Prism")
        arcade_button.setObjectName("route_media")
        arcade_button.setAccessibleName("Open Arcade and play Snake or Tetris")
        arcade_button.clicked.connect(lambda: self.handle_navigation("arcade"))
        layout.addWidget(arcade_button)

        layout.addStretch(1)
        return page

    def _build_music_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(32, 30, 32, 24)
        layout.setSpacing(12)

        eyebrow = QLabel("PRISM  /  LIBRARY")
        eyebrow.setObjectName("eyebrow")
        layout.addWidget(eyebrow)

        self.music_page_title = QLabel("Music & Audio")
        self.music_page_title.setObjectName("page_title")
        layout.addWidget(self.music_page_title)

        self.source_controls = QWidget()
        source_row = QHBoxLayout(self.source_controls)
        source_row.setContentsMargins(0, 0, 0, 0)
        source_row.setSpacing(8)
        self.source_selector = QComboBox()
        self.source_selector.setObjectName("music_source")
        self.source_selector.addItem("Jamendo", "jamendo")
        self.source_selector.addItem("Local files", "local")
        self.source_selector.addItem("Supabase library", "supabase")
        self.source_selector.setAccessibleName("Music source")
        source_row.addWidget(self.source_selector)

        self.genre_selector = QComboBox()
        self.genre_selector.setObjectName("music_genre")
        for label, tag in JAMENDO_GENRES.items():
            self.genre_selector.addItem(label, tag)
        self.genre_selector.setAccessibleName("Jamendo genre")
        source_row.addWidget(self.genre_selector)

        self.choose_folder_button = QPushButton("Choose folder")
        self.choose_folder_button.setObjectName("music_action")
        self.choose_folder_button.clicked.connect(self.choose_local_music_folder)
        source_row.addWidget(self.choose_folder_button)

        self.search_music_button = QPushButton("Search")
        self.search_music_button.setObjectName("music_action")
        self.search_music_button.clicked.connect(self.search_music)
        source_row.addWidget(self.search_music_button)
        layout.addWidget(self.source_controls)

        self.search_bar = QLineEdit()
        self.search_bar.setObjectName("song_search")
        self.search_bar.setPlaceholderText("Search tracks or artists")
        self.search_bar.setAccessibleName("Search music tracks or artists")
        self.search_bar.textChanged.connect(self._handle_music_query_changed)
        self.search_bar.returnPressed.connect(self.search_music)
        layout.addWidget(self.search_bar)

        state_row = QHBoxLayout()
        self.music_state_label = QLabel("Search Jamendo or choose a local music folder.")
        self.music_state_label.setObjectName("body_copy")
        self.music_state_label.setWordWrap(True)
        state_row.addWidget(self.music_state_label, stretch=1)

        self.retry_button = QPushButton("Try again")
        self.retry_button.setObjectName("retry_button")
        self.retry_button.clicked.connect(self.retry_music_source)
        self.retry_button.hide()
        state_row.addWidget(self.retry_button)
        layout.addLayout(state_row)

        self.track_attribution_label = QLabel()
        self.track_attribution_label.setObjectName("track_attribution")
        self.track_attribution_label.setOpenExternalLinks(True)
        self.track_attribution_label.hide()
        layout.addWidget(self.track_attribution_label)

        self.song_table = QTableWidget()
        self.song_table.setObjectName("song_table")
        self.song_table.setColumnCount(4)
        self.song_table.setHorizontalHeaderLabels(["Title", "Artist", "Album", "Duration"])
        header = self.song_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.song_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.song_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.song_table.setAlternatingRowColors(True)
        self.song_table.viewport().setContextMenuPolicy(
            Qt.ContextMenuPolicy.DefaultContextMenu
        )
        self.song_table.viewport().installEventFilter(self)
        self.song_table.cellDoubleClicked.connect(self.handle_song_double_click)
        self.song_table.activated.connect(
            lambda index: self.handle_song_double_click(index.row(), 0)
        )
        self.song_table.cellClicked.connect(self._show_track_attribution)
        self.song_table.hide()
        layout.addWidget(self.song_table, stretch=1)

        self.source_selector.currentIndexChanged.connect(self._handle_music_source_changed)
        self.genre_selector.currentIndexChanged.connect(self._handle_genre_changed)
        self._update_music_source_controls()
        return page

    def _build_placeholder_page(self, title: str, status: str, description: str) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(38, 34, 38, 28)
        layout.setSpacing(14)

        eyebrow = QLabel("PRISM  /  IN THE WORKS")
        eyebrow.setObjectName("eyebrow")
        layout.addWidget(eyebrow)

        heading = QLabel(title)
        heading.setObjectName("page_title")
        layout.addWidget(heading)

        status_label = QLabel(status)
        status_label.setStyleSheet("color: #00D2FF; font-size: 14px; font-weight: 650;")
        layout.addWidget(status_label)

        copy = QLabel(description)
        copy.setObjectName("body_copy")
        copy.setWordWrap(True)
        copy.setMaximumWidth(540)
        layout.addWidget(copy)

        home_button = QPushButton("Back to home")
        home_button.setObjectName("home_button")
        home_button.setMaximumWidth(150)
        home_button.clicked.connect(lambda: self.handle_navigation("home"))
        layout.addWidget(home_button)
        layout.addStretch(1)
        return page

    def _show_page(self, index: int):
        if self.pages.currentIndex() == index:
            return

        for page_index in range(self.pages.count()):
            page = self.pages.widget(page_index)
            if page.graphicsEffect() is not None:
                page.setGraphicsEffect(None)

        self.pages.setCurrentIndex(index)

    def _retain_background_worker(self, worker: QThread):
        worker_id = id(worker)
        self._background_workers[worker_id] = worker
        worker.setParent(self)
        worker.finished.connect(
            self._release_background_worker,
            Qt.ConnectionType.QueuedConnection,
        )

    @pyqtSlot()
    def _release_background_worker(self):
        worker = self.sender()
        if not isinstance(worker, QThread):
            return
        worker_id = id(worker)

        QTimer.singleShot(
            0,
            lambda retained_id=worker_id: self._dispose_background_worker(
                retained_id
            ),
        )

    def _dispose_background_worker(self, worker_id: int):
        worker = self._background_workers.pop(worker_id, None)
        if worker is not None:
            worker.wait()
            worker.deleteLater()

    def _update_music_source_controls(self):
        source = self.source_selector.currentData()
        is_jamendo = source == "jamendo"
        is_local = source == "local"
        self.genre_selector.setVisible(is_jamendo)
        self.choose_folder_button.setVisible(is_local)
        self.search_music_button.setVisible(is_jamendo)
        self.search_bar.setPlaceholderText(
            "Search tracks or artists" if is_jamendo else "Filter this library"
        )
        self.track_attribution_label.hide()

    def _handle_music_source_changed(self):
        self._update_music_source_controls()
        self.search_bar.clear()
        self.current_songs = []
        self.displayed_songs = []
        self.song_table.setRowCount(0)
        self.song_table.hide()
        source = self.source_selector.currentData()

        if source == "jamendo":
            self.search_jamendo()
        elif source == "local":
            if self.local_music_folder:
                self.scan_local_music_folder(self.local_music_folder)
            else:
                self._set_music_state("Choose a folder to scan for local audio files.")
        elif source == "supabase":
            self.load_music(force=True)

    def _handle_genre_changed(self):
        if self.source_selector.currentData() == "jamendo":
            self.search_jamendo()

    def _handle_music_query_changed(self, query: str):
        if self.active_playlist_id or self.source_selector.currentData() in (
            "local",
            "supabase",
        ):
            self.filter_songs(query)

    def search_music(self):
        source = self.source_selector.currentData()
        if self.active_playlist_id:
            self.filter_songs(self.search_bar.text())
        elif source == "jamendo":
            self.search_jamendo()
        elif source in ("local", "supabase"):
            self.filter_songs(self.search_bar.text())

    def retry_music_source(self):
        source = self.source_selector.currentData()
        if source == "jamendo":
            self.search_jamendo()
        elif source == "local" and self.local_music_folder:
            self.scan_local_music_folder(self.local_music_folder)
        elif source == "local":
            self.choose_local_music_folder()
        elif source == "supabase":
            self.load_music(force=True, liked_only=self.showing_liked_songs)

    def search_jamendo(self):
        self.showing_liked_songs = False
        self.jamendo_request_id += 1
        request_id = self.jamendo_request_id
        self._set_music_state("Searching Jamendo…")
        self.jamendo_worker = JamendoSearchWorker(
            request_id,
            JAMENDO_CLIENT_ID,
            self.search_bar.text(),
            str(self.genre_selector.currentData() or ""),
        )
        self.jamendo_worker.loaded.connect(self._handle_jamendo_loaded)
        self.jamendo_worker.failed.connect(self._handle_jamendo_error)
        self._retain_background_worker(self.jamendo_worker)
        self.jamendo_worker.start()

    def _handle_jamendo_loaded(self, request_id: int, tracks: list[dict]):
        if request_id != self.jamendo_request_id:
            return
        self.jamendo_worker = None
        self.jamendo_loaded = True
        self.current_songs = tracks
        if not tracks:
            self._set_music_state(
                "No Jamendo tracks matched. Try another search or genre.",
                show_retry=True,
            )
            return
        self.filter_songs("")

    def _handle_jamendo_error(self, request_id: int, message: str):
        if request_id != self.jamendo_request_id:
            return
        self.jamendo_worker = None
        self.jamendo_loaded = False
        self._set_music_state(message, is_error=True)

    def choose_local_music_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Choose a music folder")
        if folder:
            self.local_music_folder = folder
            self.scan_local_music_folder(folder)

    def scan_local_music_folder(self, folder: str):
        self.local_scan_request_id += 1
        request_id = self.local_scan_request_id
        self._set_music_state(f"Scanning {Path(folder).name or folder} for audio files…")
        self.local_scan_worker = LocalFolderScanWorker(request_id, folder)
        self.local_scan_worker.loaded.connect(self._handle_local_folder_loaded)
        self.local_scan_worker.failed.connect(self._handle_local_folder_error)
        self._retain_background_worker(self.local_scan_worker)
        self.local_scan_worker.start()

    def _handle_local_folder_loaded(self, request_id: int, tracks: list[dict]):
        if request_id != self.local_scan_request_id:
            return
        self.local_scan_worker = None
        self.current_songs = tracks
        self.search_bar.clear()
        if not tracks:
            self._set_music_state(
                "No supported audio files found. Prism scans MP3, OGG, OGA, WAV, and FLAC files."
            )
            return
        self.filter_songs("")

    def _handle_local_folder_error(self, request_id: int, message: str):
        if request_id != self.local_scan_request_id:
            return
        self.local_scan_worker = None
        self._set_music_state(message, is_error=True)

    def load_music(self, force: bool = False, liked_only: bool = False):
        if not force and not liked_only and self.music_loaded:
            self.showing_liked_songs = False
            self.music_page_title.setText("Music & Audio")
            self.current_songs = self.all_songs
            self._display_current_songs()
            return

        self.showing_liked_songs = liked_only
        self.music_page_title.setText("Liked Songs" if liked_only else "Music & Audio")
        self.search_bar.clear()
        self._set_music_state("Loading your liked songs…" if liked_only else "Loading your music library…")
        self.load_request_id += 1
        self.music_loader = MusicLibraryLoader(self.load_request_id, self.user_id, liked_only)
        self.music_loader.loaded.connect(self._handle_library_loaded)
        self.music_loader.failed.connect(self._handle_library_error)
        self._retain_background_worker(self.music_loader)
        self.music_loader.start()

    def _handle_library_loaded(self, request_id: int, songs: list[dict]):
        if request_id != self.load_request_id:
            return
        self.music_loader = None
        if self.showing_liked_songs:
            self.current_songs = songs
        else:
            self.all_songs = songs
            self.current_songs = self.all_songs
            self.music_loaded = True

        self._display_current_songs()

    def _display_current_songs(self):
        if not self.current_songs:
            if self.showing_liked_songs:
                self._set_music_state(
                    "No liked songs yet. Double-click a song to start listening.",
                    show_retry=True,
                )
            else:
                self._set_music_state("No songs are available in your library yet.", show_retry=True)
            return
        self.filter_songs(self.search_bar.text())

    def _handle_library_error(self, request_id: int, message: str):
        if request_id != self.load_request_id:
            return
        self.music_loader = None
        self._set_music_state(message, is_error=True)
    def _set_music_state(
        self,
        message: str,
        is_error: bool = False,
        show_retry: bool = False,
    ):
        self.music_state_label.setText(message)
        self.music_state_label.setStyleSheet(
            "color: #FFAAAA;" if is_error else "color: #B7B7C7;"
        )
        self.music_state_label.show()
        self.song_table.hide()
        self.retry_button.setText("Try again" if is_error else "Refresh")
        self.retry_button.setVisible(is_error or show_retry)

    def _populate_song_table(self, songs: list[dict]):
        self.displayed_songs = list(songs)
        self.song_table.setRowCount(len(songs))
        for row, song in enumerate(songs):
            self.song_table.setItem(row, 0, QTableWidgetItem(str(song.get("title") or "Unknown")))
            self.song_table.setItem(row, 1, QTableWidgetItem(str(song.get("artist") or "Unknown")))
            self.song_table.setItem(row, 2, QTableWidgetItem(str(song.get("album") or "-")))

            try:
                duration = int(song.get("duration") or 0)
            except (TypeError, ValueError):
                duration = 0
            minutes, seconds = divmod(duration, 60)
            self.song_table.setItem(row, 3, QTableWidgetItem(f"{minutes}:{seconds:02d}"))

        self.music_state_label.hide()
        self.retry_button.hide()
        self.song_table.show()
        if songs:
            self._show_track_attribution(0, 0)

    def filter_songs(self, query: str):
        if not self.current_songs:
            return
        normalized_query = query.casefold().strip()
        filtered = [
            song
            for song in self.current_songs
            if normalized_query in str(song.get("title") or "").casefold()
            or normalized_query in str(song.get("artist") or "").casefold()
        ]
        if not filtered:
            self.displayed_songs = []
            self.song_table.setRowCount(0)
            self.track_attribution_label.hide()
            self._set_music_state("No songs match that search.")
            return
        self._populate_song_table(filtered)

    def _show_track_attribution(self, row: int, column: int):
        if row >= len(self.displayed_songs):
            self.track_attribution_label.hide()
            return
        track = self.displayed_songs[row]
        if track.get("source") != "jamendo":
            self.track_attribution_label.hide()
            return

        title = html.escape(str(track.get("title") or "Jamendo track"))
        share_url = str(track.get("share_url") or "")
        license_url = str(track.get("license_url") or "")
        details = []
        if share_url.startswith("https://"):
            details.append(f'<a href="{html.escape(share_url, quote=True)}">{title} on Jamendo</a>')
        else:
            details.append("Jamendo catalog")
        if license_url.startswith(("https://", "http://")):
            details.append(
                f'<a href="{html.escape(license_url, quote=True)}">Track license</a>'
            )
        self.track_attribution_label.setText(" · ".join(details))
        self.track_attribution_label.show()

    def handle_song_double_click(self, row: int, column: int):
        if row >= len(self.displayed_songs):
            return
        self.playback_queue.replace(self.displayed_songs, row)
        self._queue_completion_handled = False
        self._play_queue_item(row)

    def _play_queue_item(self, index: int):
        try:
            self.playback_queue.play_index(index)
        except IndexError:
            return
        song = self.playback_queue.tracks[index]
        self._queue_transition_pending = True
        self.audio_request_id += 1
        request_id = self.audio_request_id
        audio_path = song.get("audio_path")
        if audio_path:
            if self.player.play_file(audio_path, song):
                self._finish_track_start(song)
            else:
                self._handle_track_start_error(
                    "Prism couldn't play that local audio file."
                )
            return

        audio_url = song.get("audio_url")
        if not audio_url:
            self._handle_track_start_error(
                "This track does not have a playable audio URL."
            )
            return
        self.music_state_label.setText("Loading audio…")
        self.music_state_label.setStyleSheet("color: #B7B7C7;")
        self.music_state_label.show()
        self.retry_button.hide()
        worker = AudioDownloadWorker(request_id, song)
        worker.setParent(self)
        self.audio_download_workers[request_id] = worker
        worker.loaded.connect(self._handle_audio_loaded)
        worker.failed.connect(self._handle_audio_error)
        self._retain_background_worker(worker)
        worker.start()

    def _handle_audio_loaded(self, request_id: int, song: dict, audio_data: bytes):
        self.audio_download_workers.pop(request_id, None)
        if request_id != self.audio_request_id:
            return
        if self.player.play_bytes(audio_data, song):
            self._finish_track_start(song)
        else:
            self._handle_track_start_error(
                "Prism couldn't decode this audio stream."
            )

    def _handle_audio_error(self, request_id: int, message: str):
        self.audio_download_workers.pop(request_id, None)
        if request_id != self.audio_request_id:
            return
        self._handle_track_start_error(message)

    def _finish_track_start(self, song: dict):
        self._queue_transition_pending = False
        self._queue_completion_handled = False
        self.music_state_label.hide()
        self.player_bar.set_track_info(
            str(song.get("title") or "Unknown"),
            str(song.get("artist") or "Unknown"),
        )
        self.player_bar.set_playing_state(True)
        self.player_bar.set_timeline(0, int(song.get("duration") or 0))
        self._update_queue_dialog()

    def _handle_track_start_error(self, message: str):
        self._queue_transition_pending = False
        self._queue_completion_handled = True
        self._show_playback_error(message)
        failed_index = self.playback_queue.current_index
        if self.player.current_song:
            self.player.stop()
        self.player_bar.set_playing_state(False)

        next_index = None
        if self.playback_queue.repeat_mode != "one":
            next_index = self.playback_queue.next_index()
        if next_index is not None and next_index != failed_index:
            QTimer.singleShot(0, lambda: self._play_queue_item(next_index))
        else:
            self.player_bar.set_track_info(
                "Track unavailable",
                "See Music & Audio for details",
            )
            self.player_bar.set_timeline(0, 0)

    def _show_playback_error(self, message: str):
        self.music_state_label.setText(message)
        self.music_state_label.setStyleSheet("color: #FFAAAA;")
        self.music_state_label.show()
        self.retry_button.hide()

    def _update_playback_timeline(self):
        song = self.player.current_song
        if song:
            duration = max(0, int(song.get("duration") or 0))
            position = int(self.player.position_seconds())
            self.player_bar.set_timeline(position, duration)
            if (
                not self.player.is_paused
                and not self._queue_transition_pending
                and not self._queue_completion_handled
                and not self.player.is_playing()
            ):
                self._queue_completion_handled = True
                self.handle_next_track()

    def handle_play_toggle(self):
        if not self.player.current_song:
            if self.playback_queue.tracks:
                index = max(0, self.playback_queue.current_index)
                self._play_queue_item(index)
                return
            selected_row = self.song_table.currentRow()
            if (
                self.pages.currentIndex() == 1
                and 0 <= selected_row < len(self.displayed_songs)
            ):
                self.playback_queue.replace(self.displayed_songs, selected_row)
                self._play_queue_item(selected_row)
                return
            self.handle_navigation("music")
            return

        if self.player.is_playing():
            self.player.pause()
            self.player_bar.set_playing_state(False)
        else:
            self.player.resume()
            self.player_bar.set_playing_state(True)

    def handle_seek(self, position: int):
        if self.player.seek(position):
            return
        QMessageBox.information(
            self,
            "Seeking unavailable",
            "This track's audio format does not support seeking.",
        )

    def handle_previous_track(self):
        if not self.playback_queue.tracks:
            return
        position = self.player.position_seconds()
        if position > 5:
            if self.player.seek(0):
                return
        index = self.playback_queue.previous_index(position)
        if index is not None:
            self._play_queue_item(index)

    def handle_next_track(self):
        index = self.playback_queue.next_index()
        if index is not None:
            self._play_queue_item(index)
            return
        if self.player.current_song:
            self.player.stop()
            self.player_bar.set_playing_state(False)
            self.player_bar.set_track_info(
                "Queue finished",
                "Add tracks or enable repeat",
            )
            self.player_bar.set_timeline(0, 0)
        self._update_queue_dialog()

    def handle_shuffle_toggled(self):
        self.playback_queue.shuffle_enabled = not self.playback_queue.shuffle_enabled
        self.player_bar.set_shuffle_state(self.playback_queue.shuffle_enabled)

    def handle_repeat_cycle(self):
        modes = ("off", "all", "one")
        current = modes.index(self.playback_queue.repeat_mode)
        self.playback_queue.repeat_mode = modes[(current + 1) % len(modes)]
        self.player_bar.set_repeat_state(self.playback_queue.repeat_mode)

    def handle_show_queue(self):
        if self.queue_dialog is None:
            self.queue_dialog = QueueDialog(self)
            self.queue_dialog.track_activated.connect(self._play_queue_item)
            self.queue_dialog.remove_requested.connect(self._remove_queue_track)
            self.queue_dialog.clear_requested.connect(self._clear_queue)
        self._update_queue_dialog()
        self.queue_dialog.show()
        self.queue_dialog.raise_()
        self.queue_dialog.activateWindow()

    def _update_queue_dialog(self):
        if self.queue_dialog is not None:
            self.queue_dialog.set_tracks(
                self.playback_queue.tracks,
                self.playback_queue.current_index,
            )

    def _remove_queue_track(self, index: int):
        if self.playback_queue.remove(index):
            self._update_queue_dialog()

    def _clear_queue(self):
        self.playback_queue.clear()
        self.player.stop()
        self._queue_transition_pending = False
        self._queue_completion_handled = True
        self.player_bar.set_track_info(
            "No track selected",
            "Choose a song from Music & Audio",
        )
        self.player_bar.set_playing_state(False)
        self.player_bar.set_timeline(0, 0)
        self._update_queue_dialog()

    def eventFilter(self, watched, event):
        if (
            watched is self.song_table.viewport()
            and event.type() == QEvent.Type.ContextMenu
        ):
            context_event = event
            if isinstance(context_event, QContextMenuEvent):
                self._show_track_menu(
                    context_event.pos(),
                    context_event.globalPos(),
                )
                return True
        return super().eventFilter(watched, event)

    def _show_track_menu(self, position, global_position=None):
        row = self.song_table.indexAt(position).row()
        if row < 0 and (position.x() < 0 or position.y() < 0):
            row = self.song_table.currentRow()
        if row < 0 or row >= len(self.displayed_songs):
            return
        self.song_table.selectRow(row)
        song = self.displayed_songs[row]

        menu = QMenu(self)
        play_action = menu.addAction("Play now")
        queue_action = menu.addAction("Add to queue")
        remove_action = None
        playlist_actions = {}
        if self.active_playlist_id:
            remove_action = menu.addAction("Remove from playlist")
        else:
            playlist_menu = menu.addMenu("Add to playlist")
            if song.get("source") not in ("jamendo", "local"):
                unsupported_action = playlist_menu.addAction(
                    "Only Jamendo and local tracks can be saved"
                )
                unsupported_action.setEnabled(False)
            elif not self.playlists:
                no_playlists_action = playlist_menu.addAction("Create a playlist first")
                no_playlists_action.setEnabled(False)
            else:
                for playlist in self.playlists.values():
                    action = playlist_menu.addAction(
                        str(playlist.get("name") or "Untitled")
                    )
                    action.setData(str(playlist["id"]))
                    playlist_actions[action] = str(playlist["id"])
        menu_position = (
            global_position
            if global_position is not None
            else self.song_table.viewport().mapToGlobal(position)
        )
        selected = menu.exec(menu_position)

        if selected == play_action:
            self.playback_queue.replace([song], 0)
            self._play_queue_item(0)
        elif selected == queue_action:
            index = self.playback_queue.add(song)
            self._update_queue_dialog()
            if not self.player.current_song:
                self._play_queue_item(index)
        elif remove_action is not None and selected == remove_action:
            self._remove_track_from_playlist(song)
        elif selected in playlist_actions:
            self._add_track_to_playlist(playlist_actions[selected], song)

    def _add_track_to_playlist(self, playlist_id: str, track: dict):
        if track.get("source") == "local":
            try:
                added = add_local_playlist_track(self.user_id, playlist_id, track)
            except (OSError, sqlite3.Error, ValueError) as error:
                LOGGER.exception("Could not save a device-only playlist track")
                QMessageBox.warning(self, "Track not added", str(error))
                return
            if not added:
                QMessageBox.information(
                    self,
                    "Already in playlist",
                    "This local file is already in that playlist on this device.",
                )
                return
            if self.active_playlist_id == playlist_id:
                self._refresh_active_playlist(playlist_id)
            else:
                playlist = self.playlists.get(playlist_id, {})
                QMessageBox.information(
                    self,
                    "Added to playlist",
                    f"Added to “{playlist.get('name', 'playlist')}” on this device.",
                )
            return

        self._start_database_operation(
            ("track_added", playlist_id),
            lambda: db.add_playlist_track(self.user_id, playlist_id, track),
        )

    def _remove_track_from_playlist(self, track: dict):
        playlist_id = self.active_playlist_id
        if not playlist_id:
            return
        if track.get("source") == "local":
            try:
                removed = remove_local_playlist_track(
                    self.user_id,
                    playlist_id,
                    track,
                )
            except (OSError, sqlite3.Error, ValueError) as error:
                LOGGER.exception("Could not remove a device-only playlist track")
                QMessageBox.warning(self, "Track not removed", str(error))
                return
            if removed:
                self._refresh_active_playlist(playlist_id)
            return

        self._start_database_operation(
            ("track_removed", playlist_id),
            lambda: db.remove_playlist_track(self.user_id, playlist_id, track),
        )

    def _refresh_active_playlist(self, playlist_id: str):
        self._start_database_operation(
            ("playlist_tracks", playlist_id),
            lambda: db.fetch_playlist_tracks(self.user_id, playlist_id),
        )

    def handle_navigation(self, target: str):
        returning_from_playlist = (
            target == "music" and self.active_playlist_id is not None
        )
        self.sidebar.set_active(target)
        page_by_target = {
            "home": 0,
            "music": 1,
            "liked": 1,
            "movies": 2,
            "arcade": 3,
        }
        page_index = page_by_target.get(target)
        if page_index is None:
            return

        if target in ("music", "liked"):
            self.active_playlist_id = None
            self.source_controls.show()
            self._update_music_source_controls()
            self.search_bar.setPlaceholderText(
                "Search tracks or artists"
                if self.source_selector.currentData() == "jamendo"
                else "Filter this library"
            )
            self.music_page_title.setText(
                "Liked Songs" if target == "liked" else "Music & Audio"
            )
        self._show_page(page_index)
        if target != "arcade":
            self.arcade_view.pause_game()
        if target == "music":
            source = self.source_selector.currentData()
            if source == "jamendo" and (
                not self.jamendo_loaded or returning_from_playlist
            ):
                self.search_jamendo()
            elif source == "local" and self.local_music_folder and (
                not self.current_songs or returning_from_playlist
            ):
                self.scan_local_music_folder(self.local_music_folder)
            elif source == "local" and not self.local_music_folder:
                self._set_music_state("Choose a folder to scan for local audio files.")
            elif source == "supabase":
                self.load_music(force=returning_from_playlist)
        elif target == "liked":
            self.source_selector.blockSignals(True)
            self.source_selector.setCurrentIndex(
                self.source_selector.findData("supabase")
            )
            self.source_selector.blockSignals(False)
            self._update_music_source_controls()
            self.load_music(force=True, liked_only=True)

    def handle_playlist_selected(self, playlist_id: str):
        playlist = self.playlists.get(playlist_id)
        if not playlist:
            return
        self.active_playlist_id = playlist_id
        self.sidebar.set_active("music")
        self.source_controls.hide()
        self.search_bar.setPlaceholderText("Filter this playlist")
        self.music_page_title.setText(str(playlist.get("name") or "Playlist"))
        self._show_page(1)
        self._set_music_state("Loading playlist…")
        self._refresh_active_playlist(playlist_id)

    def _start_database_operation(self, context: tuple, operation):
        self.database_request_id += 1
        request_id = self.database_request_id
        worker = DatabaseWorker(request_id, operation)
        worker.setParent(self)
        self.database_workers[request_id] = worker
        self.database_requests[request_id] = context
        worker.result_ready.connect(self._handle_database_result)
        worker.failed.connect(self._handle_database_error)
        worker.finished.connect(
            lambda request_id=request_id: self.database_workers.pop(
                request_id, None
            )
        )
        self._retain_background_worker(worker)
        worker.start()

    def _request_playlists(self):
        self.sidebar.set_playlist_state("Loading playlists…")
        self._start_database_operation(
            ("playlists_loaded",),
            lambda: db.fetch_user_playlists(self.user_id),
        )

    def _handle_database_result(self, request_id: int, result):
        context = self.database_requests.pop(request_id, ())
        if not context:
            return
        action = context[0]
        if action == "playlists_loaded":
            self.playlists = {
                str(playlist["id"]): playlist
                for playlist in result
                if playlist.get("id") is not None
            }
            self.sidebar.update_playlists(list(self.playlists.values()))
        elif action == "playlist_created":
            self._request_playlists()
        elif action == "playlist_renamed":
            playlist_id = context[1]
            if self.active_playlist_id == playlist_id:
                self.music_page_title.setText(str(result.get("name") or "Playlist"))
            self._request_playlists()
        elif action == "playlist_deleted":
            playlist_id = context[1]
            try:
                delete_local_playlist_tracks(self.user_id, playlist_id)
            except sqlite3.Error:
                LOGGER.exception("Could not clear local tracks for a deleted playlist")
                QMessageBox.warning(
                    self,
                    "Playlist deleted",
                    "The cloud playlist was deleted, but Prism could not clear its "
                    "device-only entries from this computer.",
                )
            if self.active_playlist_id == playlist_id:
                self.active_playlist_id = None
                self.source_controls.show()
                self.music_page_title.setText("Music & Audio")
                self.current_songs = []
                self.displayed_songs = []
                self.song_table.setRowCount(0)
                self.jamendo_loaded = False
                self._set_music_state("Playlist deleted.")
            self._request_playlists()
        elif action == "playlist_tracks":
            playlist_id = context[1]
            if self.active_playlist_id != playlist_id:
                return
            try:
                local_tracks = fetch_local_playlist_tracks(self.user_id, playlist_id)
            except (OSError, sqlite3.Error, ValueError) as error:
                LOGGER.exception("Could not load device-only playlist tracks")
                QMessageBox.warning(self, "Local playlist items unavailable", str(error))
                local_tracks = []
            self.current_songs = list(result) + local_tracks
            self.search_bar.clear()
            if self.current_songs:
                self.filter_songs("")
            else:
                self._set_music_state(
                    "This playlist is empty. Add tracks from Jamendo or local files."
                )
        elif action in ("track_added", "track_removed"):
            if self.active_playlist_id == context[1]:
                self._refresh_active_playlist(context[1])
            elif action == "track_added":
                playlist = self.playlists.get(context[1], {})
                QMessageBox.information(
                    self,
                    "Added to playlist",
                    f"Added to “{playlist.get('name', 'playlist')}”.",
                )

    def _handle_database_error(self, request_id: int, message: str):
        context = self.database_requests.pop(request_id, ())
        if not context:
            return
        action = context[0]
        if action == "playlists_loaded":
            self.sidebar.set_playlist_state(
                "Playlist load failed. Check Supabase setup, then refresh."
            )
            QMessageBox.warning(
                self,
                "Playlists unavailable",
                "Prism couldn't load your playlists. Check your connection and run "
                "the Supabase playlist migration from the README.\n\n"
                f"Details: {message}",
            )
        elif action == "playlist_tracks":
            if self.active_playlist_id == context[1]:
                self._set_music_state(
                    "Couldn't load this playlist. Check Supabase setup, then try again.",
                    is_error=True,
                )
                QMessageBox.warning(
                    self,
                    "Playlist unavailable",
                    f"Prism couldn't load this playlist.\n\nDetails: {message}",
                )
        else:
            QMessageBox.warning(
                self,
                "Playlist change failed",
                f"Prism couldn't save that playlist change.\n\nDetails: {message}",
            )

    def handle_create_playlist(self, name: str):
        self._start_database_operation(
            ("playlist_created",),
            lambda: db.create_playlist(self.user_id, name),
        )

    def handle_rename_playlist(self, playlist_id: str, name: str):
        self._start_database_operation(
            ("playlist_renamed", playlist_id),
            lambda: db.rename_playlist(self.user_id, playlist_id, name),
        )

    def handle_delete_playlist(self, playlist_id: str):
        self._start_database_operation(
            ("playlist_deleted", playlist_id),
            lambda: db.delete_playlist(self.user_id, playlist_id),
        )

    def closeEvent(self, event):
        self.playback_timer.stop()
        workers = [
            *self._background_workers.values(),
            *self.audio_download_workers.values(),
            *self.database_workers.values(),
        ]
        for worker in workers:
            if worker is not None and worker.isRunning():
                worker.wait()
        self.player.stop()
        super().closeEvent(event)
