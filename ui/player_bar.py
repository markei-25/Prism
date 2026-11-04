"""Persistent Prism audio controls."""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QSlider, QVBoxLayout, QWidget


class PlayerBar(QWidget):
    play_toggled = pyqtSignal()
    volume_changed = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        self.setObjectName("player_bar")
        self.setFixedHeight(82)
        self.setStyleSheet("""
            QWidget#player_bar {
                background-color: #1A1A24;
                border-top: 1px solid #2E2E3E;
                color: #FFFFFF;
                font-family: "Segoe UI";
            }
            QLabel#track_title {
                font-size: 13px;
                font-weight: 650;
            }
            QLabel#track_artist,
            QLabel#volume_label {
                color: #B7B7C7;
                font-size: 11px;
            }
            QPushButton#play_btn {
                background-color: #00D2FF;
                border: 1px solid #00D2FF;
                border-radius: 7px;
                color: #0F0F12;
                min-width: 56px;
                max-width: 56px;
                min-height: 34px;
                max-height: 34px;
                font-size: 13px;
                font-weight: 700;
            }
            QPushButton#play_btn:hover {
                background-color: #39DFFF;
                border-color: #39DFFF;
            }
            QPushButton:focus {
                border: 2px solid #FFFFFF;
            }
            QSlider::groove:horizontal {
                height: 4px;
                background: #454554;
                border-radius: 2px;
            }
            QSlider::sub-page:horizontal {
                background: #00D2FF;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #FFFFFF;
                border: 1px solid #0F0F12;
                width: 12px;
                height: 12px;
                margin: -5px 0;
                border-radius: 6px;
            }
            QSlider:focus {
                border: 1px solid #00D2FF;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(22, 10, 22, 10)
        layout.setSpacing(18)

        track_info = QVBoxLayout()
        track_info.setSpacing(2)
        self.lbl_title = QLabel("No track selected")
        self.lbl_title.setObjectName("track_title")
        self.lbl_artist = QLabel("Choose a song from Music & Audio")
        self.lbl_artist.setObjectName("track_artist")
        track_info.addWidget(self.lbl_title)
        track_info.addWidget(self.lbl_artist)
        layout.addLayout(track_info, stretch=1)

        self.btn_play = QPushButton("Play")
        self.btn_play.setObjectName("play_btn")
        self.btn_play.setAccessibleName("Play or pause")
        self.btn_play.clicked.connect(self.play_toggled.emit)
        layout.addWidget(self.btn_play, alignment=Qt.AlignmentFlag.AlignCenter)

        volume_label = QLabel("Volume")
        volume_label.setObjectName("volume_label")
        self.slider_volume = QSlider(Qt.Orientation.Horizontal)
        self.slider_volume.setRange(0, 100)
        self.slider_volume.setValue(70)
        self.slider_volume.setFixedWidth(118)
        self.slider_volume.setAccessibleName("Volume")
        self.slider_volume.valueChanged.connect(self.volume_changed.emit)
        layout.addWidget(volume_label)
        layout.addWidget(self.slider_volume)

    def set_track_info(self, title: str, artist: str):
        self.lbl_title.setText(title)
        self.lbl_artist.setText(artist)

    def set_playing_state(self, is_playing: bool):
        self.btn_play.setText("Pause" if is_playing else "Play")
