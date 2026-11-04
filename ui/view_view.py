"""Movies and TV catalogue and local playback page."""

import logging
from pathlib import Path

from PyQt6.QtCore import QUrl, Qt
from PyQt6.QtMultimedia import QAudioOutput, QMediaPlayer
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from config import TMDB_API_KEY
from ui.movie_catalog import MovieCatalogView


LOGGER = logging.getLogger(__name__)


class ViewView(QWidget):
    """Movies and TV catalogue with an optional local-file player."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._user_seeking = False
        self._build_ui()
        self._build_player()

    def _build_ui(self):
        self.setObjectName("view_view")
        self.setStyleSheet("""
            QWidget#view_view {
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
                color: #FFFFFF;
                font-size: 28px;
                font-weight: 700;
            }
            QLabel#body_copy,
            QLabel#playback_time {
                color: #B7B7C7;
                font-size: 12px;
            }
            QLabel#video_status {
                color: #B7B7C7;
                font-size: 13px;
                padding: 8px 0;
            }
            QTabWidget::pane {
                border: 1px solid #2E2E3E;
                border-radius: 6px;
                top: -1px;
            }
            QTabBar::tab {
                background-color: #141419;
                color: #B7B7C7;
                border: 1px solid #2E2E3E;
                border-bottom: none;
                padding: 9px 16px;
            }
            QTabBar::tab:selected {
                background-color: #1A1A24;
                color: #FFFFFF;
                border-top: 2px solid #00D2FF;
            }
            QTabBar::tab:focus {
                border: 2px solid #FFFFFF;
            }
            QPushButton {
                background-color: #1A1A24;
                border: 1px solid #454554;
                border-radius: 6px;
                color: #FFFFFF;
                min-height: 38px;
                padding: 0 14px;
                font-size: 13px;
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
            QPushButton#open_video {
                background-color: #00D2FF;
                border-color: #00D2FF;
                color: #0F0F12;
            }
            QPushButton#open_video:hover {
                background-color: #39DFFF;
                border-color: #39DFFF;
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
        layout.setContentsMargins(32, 24, 32, 20)
        layout.setSpacing(10)

        eyebrow = QLabel("PRISM  /  SCREENING ROOM")
        eyebrow.setObjectName("eyebrow")
        layout.addWidget(eyebrow)

        title = QLabel("Movies & TV")
        title.setObjectName("page_title")
        layout.addWidget(title)

        self.tabs = QTabWidget()
        self.catalog_view = MovieCatalogView(TMDB_API_KEY)
        self.tabs.addTab(self.catalog_view, "Catalogue")
        self.tabs.addTab(self._build_local_player_page(), "Play a file")
        layout.addWidget(self.tabs, stretch=1)

    def _build_local_player_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        intro = QLabel("Open a video stored on this device to watch it in Prism.")
        intro.setObjectName("body_copy")
        intro.setWordWrap(True)
        layout.addWidget(intro)

        self.video_widget = QVideoWidget()
        self.video_widget.setObjectName("video_surface")
        self.video_widget.setMinimumSize(320, 220)
        self.video_widget.setStyleSheet(
            "background-color: #08080A; border: 1px solid #2E2E3E; border-radius: 6px;"
        )
        self.video_widget.setAccessibleName("Video playback")
        layout.addWidget(self.video_widget, stretch=1)

        self.video_status = QLabel("No video selected. Choose a file to begin.")
        self.video_status.setObjectName("video_status")
        self.video_status.setWordWrap(True)
        self.video_status.setAccessibleName("Video status")
        layout.addWidget(self.video_status)

        transport = QHBoxLayout()
        transport.setSpacing(10)

        self.open_button = QPushButton("Open video")
        self.open_button.setObjectName("open_video")
        self.open_button.clicked.connect(self.open_video_dialog)
        transport.addWidget(self.open_button)

        self.play_button = QPushButton("Play")
        self.play_button.setAccessibleName("Play or pause video")
        self.play_button.setEnabled(False)
        self.play_button.clicked.connect(self.toggle_playback)
        transport.addWidget(self.play_button)

        self.position_label = QLabel("0:00")
        self.position_label.setObjectName("playback_time")
        transport.addWidget(self.position_label)

        self.position_slider = QSlider(Qt.Orientation.Horizontal)
        self.position_slider.setRange(0, 0)
        self.position_slider.setAccessibleName("Video position")
        self.position_slider.setEnabled(False)
        self.position_slider.sliderPressed.connect(self._begin_seeking)
        self.position_slider.sliderReleased.connect(self._finish_seeking)
        self.position_slider.sliderMoved.connect(self._seek_to)
        transport.addWidget(self.position_slider, stretch=1)

        self.duration_label = QLabel("0:00")
        self.duration_label.setObjectName("playback_time")
        transport.addWidget(self.duration_label)

        self.volume_label = QLabel("Volume 70%")
        self.volume_label.setObjectName("body_copy")
        transport.addWidget(self.volume_label)

        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(70)
        self.volume_slider.setFixedWidth(96)
        self.volume_slider.setAccessibleName("Video volume")
        self.volume_slider.valueChanged.connect(self._set_volume)
        transport.addWidget(self.volume_slider)

        layout.addLayout(transport)

        self.file_name_label = QLabel("No file loaded")
        self.file_name_label.setObjectName("body_copy")
        self.file_name_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        layout.addWidget(self.file_name_label)
        return page

    def _build_player(self):
        self.media_player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.media_player.setAudioOutput(self.audio_output)
        self.media_player.setVideoOutput(self.video_widget)
        self.audio_output.setVolume(self.volume_slider.value() / 100)

        self.media_player.playbackStateChanged.connect(self._update_play_button)
        self.media_player.mediaStatusChanged.connect(self._update_media_status)
        self.media_player.durationChanged.connect(self._update_duration)
        self.media_player.positionChanged.connect(self._update_position)
        self.media_player.errorOccurred.connect(self._handle_playback_error)

    def open_video_dialog(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open a video",
            "",
            "Video files (*.mp4 *.mkv *.mov *.avi *.webm *.m4v);;All files (*)",
        )
        if file_path:
            self.load_video(file_path)

    def load_video(self, file_path: str):
        path = Path(file_path)
        if not path.is_file():
            self._show_error("That video file could not be found.")
            return

        self.media_player.stop()
        self.media_player.setSource(QUrl.fromLocalFile(str(path.resolve())))
        self.file_name_label.setText(path.name)
        self.video_status.setStyleSheet("color: #B7B7C7;")
        self.video_status.setText("Loading video…")
        self.play_button.setEnabled(False)
        self.position_slider.setEnabled(False)
        self.position_slider.setRange(0, 0)
        self.position_label.setText("0:00")
        self.duration_label.setText("0:00")

    def toggle_playback(self):
        state = self.media_player.playbackState()
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.media_player.pause()
        else:
            if self.media_player.mediaStatus() == QMediaPlayer.MediaStatus.EndOfMedia:
                self.media_player.setPosition(0)
            self.media_player.play()

    def _update_play_button(self, state: QMediaPlayer.PlaybackState):
        is_playing = state == QMediaPlayer.PlaybackState.PlayingState
        self.play_button.setText("Pause" if is_playing else "Play")
        self.play_button.setAccessibleName("Pause video" if is_playing else "Play video")

    def _update_media_status(self, status: QMediaPlayer.MediaStatus):
        if status in (
            QMediaPlayer.MediaStatus.LoadedMedia,
            QMediaPlayer.MediaStatus.BufferedMedia,
        ):
            self.video_status.setStyleSheet("color: #B7B7C7;")
            self.video_status.setText("Video ready.")
            self.play_button.setEnabled(True)
            self.position_slider.setEnabled(self.media_player.duration() > 0)
        elif status == QMediaPlayer.MediaStatus.EndOfMedia:
            self.video_status.setStyleSheet("color: #B7B7C7;")
            self.video_status.setText("Playback finished.")
        elif status == QMediaPlayer.MediaStatus.BufferingMedia:
            self.video_status.setStyleSheet("color: #B7B7C7;")
            self.video_status.setText("Buffering video…")
        elif status == QMediaPlayer.MediaStatus.StalledMedia:
            self.video_status.setStyleSheet("color: #B7B7C7;")
            self.video_status.setText("Playback paused while waiting for video data.")
        elif status == QMediaPlayer.MediaStatus.InvalidMedia:
            self._show_error(
                "Prism could not open this video. The file may be damaged or use an unsupported format."
            )

    def _update_duration(self, duration_ms: int):
        self.position_slider.setRange(0, max(0, duration_ms))
        self.position_slider.setEnabled(duration_ms > 0)
        self.duration_label.setText(self._format_time(duration_ms))

    def _update_position(self, position_ms: int):
        if not self._user_seeking:
            self.position_slider.setValue(position_ms)
        self.position_label.setText(self._format_time(position_ms))

    def _begin_seeking(self):
        self._user_seeking = True

    def _finish_seeking(self):
        self._user_seeking = False
        self.media_player.setPosition(self.position_slider.value())

    def _seek_to(self, position_ms: int):
        self.position_label.setText(self._format_time(position_ms))

    def _set_volume(self, value: int):
        self.audio_output.setVolume(value / 100)
        self.volume_label.setText(f"Volume {value}%")

    def _handle_playback_error(
        self,
        error: QMediaPlayer.Error,
        error_string: str,
    ):
        if error == QMediaPlayer.Error.NoError:
            return
        detail = error_string.strip() or "Check that the file is a supported video."
        LOGGER.warning("Video playback failed: %s", detail)
        self._show_error(f"Video playback failed: {detail}")

    def _show_error(self, message: str):
        self.video_status.setStyleSheet("color: #FFAAAA;")
        self.video_status.setText(message)
        self.play_button.setEnabled(False)
        self.position_slider.setEnabled(False)

    @staticmethod
    def _format_time(milliseconds: int) -> str:
        total_seconds = max(0, milliseconds // 1000)
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        if hours:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        return f"{minutes}:{seconds:02d}"
