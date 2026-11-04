"""Prism media hub window and destination views."""

import logging

from PyQt6.QtCore import QEasingCurve, QPropertyAnimation, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from player import AudioPlayer
from ui.player_bar import PlayerBar
from ui.sidebar import Sidebar
from ui.view_view import ViewView
import db


LOGGER = logging.getLogger(__name__)


class MusicLibraryLoader(QThread):
    loaded = pyqtSignal(int, list, list)
    failed = pyqtSignal(int)

    def __init__(self, request_id: int, user_id: str, liked_only: bool):
        super().__init__()
        self.request_id = request_id
        self.user_id = user_id
        self.liked_only = liked_only

    def run(self):
        try:
            if self.liked_only:
                songs = db.fetch_liked_songs(self.user_id)
                playlists = []
            else:
                songs = db.fetch_all_songs()
                playlists = db.fetch_user_playlists(self.user_id)
            self.loaded.emit(self.request_id, songs, playlists)
        except Exception:
            LOGGER.exception("Could not load the Prism music library")
            self.failed.emit(self.request_id)


class MainWindow(QMainWindow):
    def __init__(self, user_id: str):
        super().__init__()
        self.user_id = user_id
        self.player = AudioPlayer()
        self.all_songs: list[dict] = []
        self.current_songs: list[dict] = []
        self.displayed_songs: list[dict] = []
        self.music_loaded = False
        self.showing_liked_songs = False
        self.music_loader: MusicLibraryLoader | None = None
        self.load_request_id = 0

        self.init_ui()

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
            QPushButton#route_future {
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
            QPushButton#route_future {
                min-height: 56px;
                color: #E5E5EC;
                font-size: 14px;
            }
            QPushButton#route_music:hover,
            QPushButton#route_future:hover {
                background-color: #22222C;
                border-color: #00D2FF;
            }
            QPushButton#route_music:focus,
            QPushButton#route_future:focus,
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
        body.addWidget(self.sidebar)

        self.pages = QStackedWidget()
        self.pages.addWidget(self._build_home_page())
        self.pages.addWidget(self._build_music_page())
        self.pages.addWidget(ViewView())
        self.pages.addWidget(
            self._build_placeholder_page(
                "Arcade",
                "Planned",
                "Prism's arcade space is planned as an in-app mini-game module.",
            )
        )
        body.addWidget(self.pages, stretch=1)
        root_layout.addLayout(body, stretch=1)

        self.player_bar = PlayerBar()
        self.player_bar.play_toggled.connect(self.handle_play_toggle)
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
            "Music is available now. Movies & TV are next, with Arcade planned."
        )
        description.setObjectName("body_copy")
        layout.addWidget(description)
        layout.addSpacing(15)

        music_button = QPushButton("Music & Audio\nOpen your song library and playlists")
        music_button.setObjectName("route_music")
        music_button.setAccessibleName("Open Music and Audio")
        music_button.clicked.connect(lambda: self.handle_navigation("music"))
        layout.addWidget(music_button)

        movies_button = QPushButton("Movies & TV\nComing soon")
        movies_button.setObjectName("route_future")
        movies_button.setAccessibleName("Open Movies and TV, coming soon")
        movies_button.clicked.connect(lambda: self.handle_navigation("movies"))
        layout.addWidget(movies_button)

        arcade_button = QPushButton("Arcade\nPlanned for a later step")
        arcade_button.setObjectName("route_future")
        arcade_button.setAccessibleName("Open Arcade, planned")
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

        self.search_bar = QLineEdit()
        self.search_bar.setObjectName("song_search")
        self.search_bar.setPlaceholderText("Search by song or artist")
        self.search_bar.setAccessibleName("Search songs and artists")
        self.search_bar.textChanged.connect(self.filter_songs)
        layout.addWidget(self.search_bar)

        state_row = QHBoxLayout()
        self.music_state_label = QLabel("Your music library will appear here.")
        self.music_state_label.setObjectName("body_copy")
        self.music_state_label.setWordWrap(True)
        state_row.addWidget(self.music_state_label, stretch=1)

        self.retry_button = QPushButton("Try again")
        self.retry_button.setObjectName("retry_button")
        self.retry_button.clicked.connect(
            lambda: self.load_music(force=True, liked_only=self.showing_liked_songs)
        )
        self.retry_button.hide()
        state_row.addWidget(self.retry_button)
        layout.addLayout(state_row)

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
        self.song_table.cellDoubleClicked.connect(self.handle_song_double_click)
        self.song_table.hide()
        layout.addWidget(self.song_table, stretch=1)
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

        if hasattr(self, "_page_animation"):
            self._page_animation.stop()
        self.pages.setCurrentIndex(index)
        page = self.pages.widget(index)
        effect = QGraphicsOpacityEffect(page)
        page.setGraphicsEffect(effect)
        effect.setOpacity(0.72)

        animation = QPropertyAnimation(effect, b"opacity", self)
        animation.setDuration(160)
        animation.setStartValue(0.72)
        animation.setEndValue(1.0)
        animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._page_animation = animation
        animation.start()

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
        if not liked_only:
            self.sidebar.set_playlist_state("Loading playlists…")
        self.load_request_id += 1
        self.music_loader = MusicLibraryLoader(self.load_request_id, self.user_id, liked_only)
        self.music_loader.loaded.connect(self._handle_library_loaded)
        self.music_loader.failed.connect(self._handle_library_error)
        self.music_loader.finished.connect(self.music_loader.deleteLater)
        self.music_loader.start()

    def _handle_library_loaded(self, request_id: int, songs: list[dict], playlists: list[dict]):
        if request_id != self.load_request_id:
            return
        self.music_loader = None
        if self.showing_liked_songs:
            self.current_songs = songs
        else:
            self.all_songs = songs
            self.current_songs = self.all_songs
            self.music_loaded = True
            self.sidebar.update_playlists(playlists)

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

    def _handle_library_error(self, request_id: int):
        if request_id != self.load_request_id:
            return
        self.music_loader = None
        self._set_music_state(
            "Couldn't load the music library. Check your connection, then try again.",
            is_error=True,
        )
        if not self.showing_liked_songs:
            self.sidebar.set_playlist_state("Playlist load failed")

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
            self._set_music_state("No songs match that search.")
            return
        self._populate_song_table(filtered)

    def handle_song_double_click(self, row: int, column: int):
        if row >= len(self.displayed_songs):
            return
        song = self.displayed_songs[row]
        audio_url = song.get("audio_url")
        if not audio_url:
            QMessageBox.information(
                self,
                "Track unavailable",
                "This song does not have a playable audio URL yet.",
            )
            return
        if self.player.play_url(audio_url, song):
            self.player_bar.set_track_info(
                str(song.get("title") or "Unknown"),
                str(song.get("artist") or "Unknown"),
            )
            self.player_bar.set_playing_state(True)
        else:
            QMessageBox.warning(self, "Playback failed", "Prism couldn't start this track.")

    def handle_play_toggle(self):
        if not self.player.current_song:
            self.handle_navigation("music")
            return

        if self.player.is_playing():
            self.player.pause()
            self.player_bar.set_playing_state(False)
        else:
            self.player.resume()
            self.player_bar.set_playing_state(True)

    def handle_navigation(self, target: str):
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

        self._show_page(page_index)
        if target == "music":
            self.load_music()
        elif target == "liked":
            self.load_music(force=True, liked_only=True)

    def handle_create_playlist(self, name: str):
        playlist = db.create_playlist(self.user_id, name)
        if not playlist:
            QMessageBox.warning(self, "Playlist not created", "Prism couldn't save that playlist.")
            return
        try:
            playlists = db.fetch_user_playlists(self.user_id)
        except Exception:
            LOGGER.exception("Could not refresh Prism playlists")
            QMessageBox.warning(
                self,
                "Playlist saved",
                "The playlist was saved, but Prism couldn't refresh your library.",
            )
            return
        self.sidebar.update_playlists(playlists)
