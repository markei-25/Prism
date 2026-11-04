"""Queue inspection and editing dialog."""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
)


class QueueDialog(QDialog):
    track_activated = pyqtSignal(int)
    remove_requested = pyqtSignal(int)
    clear_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Playback queue")
        self.setMinimumSize(420, 400)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        self.heading = QLabel("Up next")
        self.heading.setStyleSheet("font-size: 19px; font-weight: 700;")
        layout.addWidget(self.heading)

        self.track_list = QListWidget()
        self.track_list.setAccessibleName("Playback queue")
        self.track_list.itemActivated.connect(self._activate_item)
        self.track_list.currentRowChanged.connect(self._update_remove_button)
        layout.addWidget(self.track_list, stretch=1)

        controls = QHBoxLayout()
        self.remove_button = QPushButton("Remove selected")
        self.remove_button.clicked.connect(self._remove_selected)
        controls.addWidget(self.remove_button)
        self.clear_button = QPushButton("Clear queue")
        self.clear_button.clicked.connect(self.clear_requested.emit)
        controls.addWidget(self.clear_button)
        controls.addStretch(1)
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        controls.addWidget(close_button)
        layout.addLayout(controls)

    def set_tracks(self, tracks: list[dict], current_index: int):
        self.track_list.clear()
        self.current_index = current_index
        self.heading.setText(f"Up next · {len(tracks)} tracks")
        if not tracks:
            empty_item = QListWidgetItem(
                "Queue is empty. Add a track from Music & Audio."
            )
            empty_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self.track_list.addItem(empty_item)
        for index, track in enumerate(tracks):
            title = str(track.get("title") or "Unknown")
            artist = str(track.get("artist") or "Unknown artist")
            prefix = "Now playing · " if index == current_index else ""
            item = QListWidgetItem(f"{prefix}{title}  ·  {artist}")
            item.setData(Qt.ItemDataRole.UserRole, index)
            self.track_list.addItem(item)
        self.remove_button.setEnabled(False)
        self.clear_button.setEnabled(bool(tracks))

    def _activate_item(self, item: QListWidgetItem):
        index = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(index, int):
            self.track_activated.emit(index)

    def _remove_selected(self):
        item = self.track_list.currentItem()
        if item is None:
            return
        index = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(index, int):
            self.remove_requested.emit(index)

    def _update_remove_button(self, row: int):
        item = self.track_list.item(row) if row >= 0 else None
        index = item.data(Qt.ItemDataRole.UserRole) if item else None
        self.remove_button.setEnabled(
            isinstance(index, int) and index != self.current_index
        )
