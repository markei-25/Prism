"""Persistent Prism audio controls."""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFontMetrics
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSlider,
    QVBoxLayout,
    QWidget,
)


class PlayerBar(QWidget):
    play_toggled = pyqtSignal()
    previous_requested = pyqtSignal()
    next_requested = pyqtSignal()
    queue_requested = pyqtSignal()
    shuffle_toggled = pyqtSignal()
    repeat_cycle_requested = pyqtSignal()
    seek_requested = pyqtSignal(int)
    volume_changed = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        self.setObjectName("player_bar")
        self.setFixedHeight(124)
        self._track_title = "No track selected"
        self._track_artist = "Choose a song from Music & Audio"
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
            QLabel#volume_label,
            QLabel#timeline_time {
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
            QPushButton#player_control {
                background-color: transparent;
                border: 1px solid transparent;
                border-radius: 5px;
                color: #D0D0DC;
                min-height: 30px;
                padding: 0 7px;
            }
            QPushButton#player_control:hover {
                background-color: #25252D;
                color: #FFFFFF;
            }
            QPushButton#player_control:checked {
                border-color: #00D2FF;
                color: #FFFFFF;
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

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 8, 22, 9)
        layout.setSpacing(7)

        timeline = QHBoxLayout()
        timeline.setSpacing(9)
        self.lbl_position = QLabel("0:00")
        self.lbl_position.setObjectName("timeline_time")
        self.slider_timeline = QSlider(Qt.Orientation.Horizontal)
        self.slider_timeline.setRange(0, 0)
        self.slider_timeline.setEnabled(False)
        self.slider_timeline.setAccessibleName("Playback position")
        self.slider_timeline.setToolTip("Seek within the current track")
        self.slider_timeline.sliderReleased.connect(
            lambda: self.seek_requested.emit(self.slider_timeline.value())
        )
        self.lbl_duration = QLabel("0:00")
        self.lbl_duration.setObjectName("timeline_time")
        timeline.addWidget(self.lbl_position)
        timeline.addWidget(self.slider_timeline, stretch=1)
        timeline.addWidget(self.lbl_duration)
        layout.addLayout(timeline)

        controls = QHBoxLayout()
        controls.setSpacing(8)

        track_info = QVBoxLayout()
        track_info.setSpacing(2)
        self.lbl_title = QLabel("No track selected")
        self.lbl_title.setObjectName("track_title")
        self.lbl_title.setSizePolicy(
            QSizePolicy.Policy.Ignored,
            QSizePolicy.Policy.Preferred,
        )
        self.lbl_artist = QLabel("Choose a song from Music & Audio")
        self.lbl_artist.setObjectName("track_artist")
        self.lbl_artist.setSizePolicy(
            QSizePolicy.Policy.Ignored,
            QSizePolicy.Policy.Preferred,
        )
        track_info.addWidget(self.lbl_title)
        track_info.addWidget(self.lbl_artist)
        controls.addLayout(track_info, stretch=1)

        self.btn_previous = self._control_button("Previous", "Previous track")
        self.btn_previous.clicked.connect(self.previous_requested.emit)
        controls.addWidget(self.btn_previous)

        self.btn_play = QPushButton("Play")
        self.btn_play.setObjectName("play_btn")
        self.btn_play.setAccessibleName("Play or pause")
        self.btn_play.clicked.connect(self.play_toggled.emit)
        controls.addWidget(self.btn_play)

        self.btn_next = self._control_button("Next", "Next track")
        self.btn_next.clicked.connect(self.next_requested.emit)
        controls.addWidget(self.btn_next)

        self.btn_queue = self._control_button("Queue", "View and edit playback queue")
        self.btn_queue.clicked.connect(self.queue_requested.emit)
        controls.addWidget(self.btn_queue)

        self.btn_shuffle = self._control_button("Shuffle off", "Toggle shuffle")
        self.btn_shuffle.setCheckable(True)
        self.btn_shuffle.clicked.connect(self.shuffle_toggled.emit)
        controls.addWidget(self.btn_shuffle)

        self.btn_repeat = self._control_button("Repeat off", "Cycle repeat mode")
        self.btn_repeat.clicked.connect(self.repeat_cycle_requested.emit)
        controls.addWidget(self.btn_repeat)

        volume_label = QLabel("Volume")
        volume_label.setObjectName("volume_label")
        self.slider_volume = QSlider(Qt.Orientation.Horizontal)
        self.slider_volume.setRange(0, 100)
        self.slider_volume.setValue(70)
        self.slider_volume.setFixedWidth(92)
        self.slider_volume.setAccessibleName("Volume")
        self.slider_volume.valueChanged.connect(self.volume_changed.emit)
        controls.addWidget(volume_label)
        controls.addWidget(self.slider_volume)
        layout.addLayout(controls)

    def _control_button(self, text: str, accessible_name: str) -> QPushButton:
        button = QPushButton(text)
        button.setObjectName("player_control")
        button.setAccessibleName(accessible_name)
        return button

    def set_track_info(self, title: str, artist: str):
        self._track_title = title
        self._track_artist = artist
        self._update_track_labels()

    def set_playing_state(self, is_playing: bool):
        self.btn_play.setText("Pause" if is_playing else "Play")

    def set_timeline(self, position: int, duration: int):
        duration = max(0, int(duration))
        position = max(0, min(int(position), duration))
        self.slider_timeline.setEnabled(duration > 0)
        self.slider_timeline.setRange(0, duration)
        if not self.slider_timeline.isSliderDown():
            self.slider_timeline.setValue(position)
        self.lbl_position.setText(self._format_time(position))
        self.lbl_duration.setText(self._format_time(duration))

    def set_shuffle_state(self, enabled: bool):
        self.btn_shuffle.setChecked(enabled)
        self.btn_shuffle.setText("Shuffle on" if enabled else "Shuffle off")
        self.btn_shuffle.setAccessibleName(
            "Turn shuffle off" if enabled else "Turn shuffle on"
        )

    def set_repeat_state(self, mode: str):
        labels = {"off": "Repeat off", "all": "Repeat all", "one": "Repeat one"}
        self.btn_repeat.setText(labels[mode])
        self.btn_repeat.setAccessibleName(f"Repeat mode: {mode}")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_track_labels()

    def _update_track_labels(self):
        for label, text in (
            (self.lbl_title, self._track_title),
            (self.lbl_artist, self._track_artist),
        ):
            label.setToolTip(text)
            metrics = QFontMetrics(label.font())
            label.setText(
                metrics.elidedText(
                    text,
                    Qt.TextElideMode.ElideRight,
                    max(1, label.width()),
                )
            )

    @staticmethod
    def _format_time(seconds: int) -> str:
        minutes, remaining_seconds = divmod(max(0, seconds), 60)
        return f"{minutes}:{remaining_seconds:02d}"
