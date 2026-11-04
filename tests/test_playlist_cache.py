import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ui import playlist_cache


class PlaylistCacheTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.database_path = self.root / "playlist_items.sqlite3"
        self.audio_path = self.root / "track.mp3"
        self.audio_path.write_bytes(b"fixture")
        self.track = {
            "title": "Local track",
            "artist": "Local file",
            "source": "local",
            "audio_path": str(self.audio_path),
        }
        self.database_patch = patch.object(
            playlist_cache,
            "DATABASE_PATH",
            self.database_path,
        )
        self.database_patch.start()

    def tearDown(self):
        self.database_patch.stop()
        self.temp_dir.cleanup()

    def test_local_playlist_items_are_scoped_to_user_and_device_database(self):
        self.assertTrue(
            playlist_cache.add_local_playlist_track("user-a", "playlist-1", self.track)
        )
        self.assertFalse(
            playlist_cache.add_local_playlist_track("user-a", "playlist-1", self.track)
        )
        saved = playlist_cache.fetch_local_playlist_tracks("user-a", "playlist-1")

        self.assertEqual(len(saved), 1)
        self.assertTrue(saved[0]["device_only"])
        self.assertEqual(
            playlist_cache.fetch_local_playlist_tracks("user-b", "playlist-1"),
            [],
        )

    def test_local_track_can_be_removed_and_playlist_cache_cleared(self):
        playlist_cache.add_local_playlist_track("user-a", "playlist-1", self.track)

        self.assertTrue(
            playlist_cache.remove_local_playlist_track(
                "user-a",
                "playlist-1",
                self.track,
            )
        )
        playlist_cache.add_local_playlist_track("user-a", "playlist-1", self.track)
        playlist_cache.delete_local_playlist_tracks("user-a", "playlist-1")
        self.assertEqual(
            playlist_cache.fetch_local_playlist_tracks("user-a", "playlist-1"),
            [],
        )


if __name__ == "__main__":
    unittest.main()
