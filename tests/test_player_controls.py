import os
import unittest
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtGui import QContextMenuEvent
from PyQt6.QtWidgets import QApplication, QMessageBox, QTableWidgetItem

from ui.main_window import MainWindow
from ui.player_bar import PlayerBar
from ui.queue_dialog import QueueDialog
from ui.sidebar import Sidebar


class PlayerControlsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_player_controls_emit_actions_and_format_timeline(self):
        bar = PlayerBar()
        actions = []
        bar.play_toggled.connect(lambda: actions.append("play"))
        bar.previous_requested.connect(lambda: actions.append("previous"))
        bar.next_requested.connect(lambda: actions.append("next"))
        bar.queue_requested.connect(lambda: actions.append("queue"))
        bar.shuffle_toggled.connect(lambda: actions.append("shuffle"))
        bar.repeat_cycle_requested.connect(lambda: actions.append("repeat"))
        bar.seek_requested.connect(lambda value: actions.append(("seek", value)))
        bar.volume_changed.connect(lambda value: actions.append(("volume", value)))

        self.assertFalse(bar.slider_timeline.isEnabled())
        bar.btn_play.click()
        bar.btn_previous.click()
        bar.btn_next.click()
        bar.btn_queue.click()
        bar.btn_shuffle.click()
        bar.btn_repeat.click()
        bar.set_timeline(65, 125)
        bar.slider_timeline.setValue(70)
        bar.slider_timeline.sliderReleased.emit()
        bar.slider_volume.setValue(40)

        self.assertEqual(
            actions,
            [
                "play",
                "previous",
                "next",
                "queue",
                "shuffle",
                "repeat",
                ("seek", 70),
                ("volume", 40),
            ],
        )
        self.assertEqual(bar.lbl_position.text(), "1:05")
        self.assertEqual(bar.lbl_duration.text(), "2:05")
        bar.set_shuffle_state(True)
        self.assertEqual(bar.btn_shuffle.text(), "Shuffle on")
        bar.set_repeat_state("one")
        self.assertEqual(bar.btn_repeat.text(), "Repeat one")

    def test_queue_dialog_can_play_remove_and_clear(self):
        dialog = QueueDialog()
        activated = []
        removed = []
        cleared = []
        dialog.track_activated.connect(activated.append)
        dialog.remove_requested.connect(removed.append)
        dialog.clear_requested.connect(lambda: cleared.append(True))
        dialog.set_tracks(
            [{"title": "Current"}, {"title": "Next"}],
            current_index=0,
        )

        dialog.track_list.setCurrentRow(0)
        self.assertFalse(dialog.remove_button.isEnabled())
        dialog.track_list.setCurrentRow(1)
        self.assertTrue(dialog.remove_button.isEnabled())
        dialog.remove_button.click()
        dialog.track_list.itemActivated.emit(dialog.track_list.item(1))
        dialog.clear_button.click()

        self.assertEqual(removed, [1])
        self.assertEqual(activated, [1])
        self.assertEqual(cleared, [True])

    def test_empty_queue_has_a_clear_state(self):
        dialog = QueueDialog()
        dialog.set_tracks([], current_index=-1)

        self.assertEqual(dialog.track_list.count(), 1)
        self.assertIn("Queue is empty", dialog.track_list.item(0).text())
        self.assertFalse(dialog.remove_button.isEnabled())
        self.assertFalse(dialog.clear_button.isEnabled())

    def test_play_button_starts_selected_library_track(self):
        track = {
            "jamendo_id": "jam-1",
            "title": "Selected track",
            "artist": "Artist",
            "source": "jamendo",
            "audio_url": "https://example.test/track.mp3",
        }
        player = Mock()
        player.current_song = None

        with (
            patch("ui.main_window.AudioPlayer", return_value=player),
            patch.object(MainWindow, "_request_playlists", lambda self: None),
        ):
            window = MainWindow("user-1")
            window.pages.setCurrentIndex(1)
            window.displayed_songs = [track]
            window.song_table.setRowCount(1)
            window.song_table.setItem(0, 0, QTableWidgetItem("Selected track"))
            window.song_table.selectRow(0)
            window._play_queue_item = Mock()

            window.handle_play_toggle()

            self.assertEqual(window.playback_queue.tracks, [track])
            self.assertEqual(window.playback_queue.current_index, 0)
            window._play_queue_item.assert_called_once_with(0)
            window.close()

    def test_sidebar_playlist_items_emit_account_playlist_id(self):
        sidebar = Sidebar()
        selected = []
        sidebar.playlist_selected.connect(selected.append)
        sidebar.update_playlists([{"id": "playlist-1", "name": "Road mix"}])

        item = sidebar.playlist_list.item(0)
        sidebar.playlist_list.itemActivated.emit(item)

        self.assertEqual(selected, ["playlist-1"])
        self.assertEqual(item.text(), "Road mix")

    def test_sidebar_create_rename_delete_and_refresh_actions(self):
        sidebar = Sidebar()
        created = []
        renamed = []
        deleted = []
        refreshed = []
        sidebar.playlist_created.connect(created.append)
        sidebar.playlist_renamed.connect(lambda *args: renamed.append(args))
        sidebar.playlist_deleted.connect(deleted.append)
        sidebar.playlists_refresh_requested.connect(lambda: refreshed.append(True))

        with patch(
            "ui.sidebar.QInputDialog.getText",
            return_value=("Road mix", True),
        ):
            sidebar.btn_add_playlist.click()
        sidebar.btn_refresh_playlists.click()
        self.assertEqual(created, ["Road mix"])
        self.assertEqual(refreshed, [True])

        sidebar.update_playlists([{"id": "p1", "name": "Road mix"}])
        sidebar.playlist_list.setCurrentRow(0)
        with (
            patch(
                "PyQt6.QtWidgets.QMenu.exec",
                new=lambda menu, position: menu.actions()[0],
            ),
            patch(
                "ui.sidebar.QInputDialog.getText",
                return_value=("Renamed", True),
            ),
        ):
            sidebar._show_playlist_menu(QPoint(-1, -1))
        self.assertEqual(renamed, [("p1", "Renamed")])

        with (
            patch(
                "PyQt6.QtWidgets.QMenu.exec",
                new=lambda menu, position: menu.actions()[1],
            ),
            patch(
                "ui.sidebar.QMessageBox.question",
                return_value=QMessageBox.StandardButton.Yes,
            ),
        ):
            sidebar._show_playlist_menu(QPoint(-1, -1))
        self.assertEqual(deleted, ["p1"])

    def test_right_clicking_track_opens_playlist_menu_action(self):
        track = {
            "jamendo_id": "jam-1",
            "title": "Track",
            "artist": "Artist",
            "source": "jamendo",
            "audio_url": "https://example.test/track.mp3",
        }
        with patch(
            "ui.main_window.db.fetch_user_playlists",
            return_value=[{"id": "playlist-1", "name": "Road mix"}],
        ):
            window = MainWindow("user-1")
            window.resize(900, 620)
            window.show()
            window.pages.setCurrentIndex(1)
            window.displayed_songs = [track]
            window.song_table.setRowCount(1)
            window.song_table.setItem(0, 0, QTableWidgetItem("Track"))
            window._add_track_to_playlist = Mock()
            self.app.processEvents()

            item_position = window.song_table.visualItemRect(
                window.song_table.item(0, 0)
            ).center()
            global_position = window.song_table.viewport().mapToGlobal(
                item_position
            )
            context_event = QContextMenuEvent(
                QContextMenuEvent.Reason.Mouse,
                item_position,
                global_position,
            )

            def choose_playlist(menu, position):
                playlist_menu = next(
                    action.menu()
                    for action in menu.actions()
                    if action.menu() is not None
                )
                return playlist_menu.actions()[0]

            with patch("PyQt6.QtWidgets.QMenu.exec", new=choose_playlist):
                QApplication.sendEvent(
                    window.song_table.viewport(),
                    context_event,
                )

            window._add_track_to_playlist.assert_called_once_with(
                "playlist-1",
                track,
            )
            window.close()


if __name__ == "__main__":
    unittest.main()
