"""Prism navigation sidebar."""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QButtonGroup,
    QInputDialog,
    QLabel,
    QListWidget,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class Sidebar(QWidget):
    navigation_changed = pyqtSignal(str)
    playlist_created = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.navigation_buttons: dict[str, QPushButton] = {}
        self.init_ui()

    def init_ui(self):
        self.setObjectName("sidebar")
        self.setMinimumWidth(196)
        self.setMaximumWidth(228)
        self.setStyleSheet("""
            QWidget#sidebar {
                background-color: #141419;
                color: #B7B7C7;
                border-right: 1px solid #2E2E3E;
            }
            QLabel#wordmark {
                color: #FFFFFF;
                font-size: 22px;
                font-weight: 700;
                padding-left: 12px;
            }
            QLabel#section_label {
                color: #A8A8BA;
                font-size: 11px;
                font-weight: 650;
                padding: 18px 12px 5px 12px;
            }
            QPushButton#nav_item {
                background-color: transparent;
                border: none;
                border-left: 3px solid transparent;
                color: #B7B7C7;
                text-align: left;
                padding: 10px 12px;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton#nav_item:hover {
                background-color: #202027;
                color: #FFFFFF;
            }
            QPushButton#nav_item:checked {
                background-color: #202027;
                border-left-color: #00D2FF;
                color: #FFFFFF;
            }
            QPushButton#nav_item:focus,
            QPushButton#add_playlist:focus {
                border: 2px solid #00D2FF;
            }
            QPushButton#add_playlist {
                background-color: transparent;
                border: 1px solid #454554;
                border-radius: 6px;
                color: #FFFFFF;
                min-height: 34px;
                text-align: left;
                padding: 0 10px;
                font-size: 12px;
            }
            QPushButton#add_playlist:hover {
                border-color: #00D2FF;
            }
            QListWidget {
                background-color: transparent;
                border: none;
                color: #C4C4D0;
                padding: 4px 2px;
            }
            QListWidget::item {
                padding: 7px 10px;
            }
            QListWidget::item:selected {
                background-color: #25252D;
                color: #FFFFFF;
            }
            QListWidget:focus {
                border: 1px solid #00D2FF;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 24, 14, 18)
        layout.setSpacing(4)

        wordmark = QLabel("PRISM")
        wordmark.setObjectName("wordmark")
        layout.addWidget(wordmark)

        navigation_heading = QLabel("Your spaces")
        navigation_heading.setObjectName("section_label")
        layout.addWidget(navigation_heading)

        self.navigation_group = QButtonGroup(self)
        self.navigation_group.setExclusive(True)
        destinations = (
            ("Home", "home"),
            ("Music & Audio", "music"),
            ("Movies & TV", "movies"),
            ("Arcade", "arcade"),
            ("Liked Songs", "liked"),
        )
        for label, target in destinations:
            button = QPushButton(label)
            button.setObjectName("nav_item")
            button.setCheckable(True)
            button.setAccessibleName(label)
            button.clicked.connect(
                lambda checked=False, destination=target: self.navigation_changed.emit(destination)
            )
            self.navigation_group.addButton(button)
            self.navigation_buttons[target] = button
            layout.addWidget(button)

        library_heading = QLabel("Your library")
        library_heading.setObjectName("section_label")
        layout.addWidget(library_heading)

        self.btn_add_playlist = QPushButton("Create playlist")
        self.btn_add_playlist.setObjectName("add_playlist")
        self.btn_add_playlist.clicked.connect(self.prompt_create_playlist)
        layout.addWidget(self.btn_add_playlist)

        self.playlist_list = QListWidget()
        self.playlist_list.setAccessibleName("Your playlists")
        self.playlist_list.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        layout.addWidget(self.playlist_list, stretch=1)
        self.set_playlist_state("Load playlists in Music.")

    def set_active(self, target: str):
        button = self.navigation_buttons.get(target)
        if button:
            button.setChecked(True)

    def prompt_create_playlist(self):
        name, ok = QInputDialog.getText(self, "Create playlist", "Playlist name:")
        if ok and name.strip():
            self.playlist_created.emit(name.strip())

    def update_playlists(self, playlists: list[dict]):
        self.playlist_list.clear()
        if not playlists:
            self.playlist_list.addItem("No playlists yet")
            return
        for playlist in playlists:
            self.playlist_list.addItem(playlist.get("name", "Untitled"))

    def set_playlist_state(self, message: str):
        self.playlist_list.clear()
        self.playlist_list.addItem(message)
