import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

from ui.music_sources import scan_audio_folder, search_jamendo_tracks


class MusicSourceTests(unittest.TestCase):
    def test_default_jamendo_catalog_uses_a_valid_popularity_order(self):
        with patch(
            "ui.music_sources._request_jamendo",
            return_value=[
                {
                    "id": "track-1",
                    "name": "First light",
                    "artist_name": "Prism Artist",
                    "audio": "https://example.test/track.mp3",
                }
            ],
        ) as request:
            tracks = search_jamendo_tracks("test-client-id")

        self.assertEqual(request.call_args.kwargs["order"], "popularity_total")
        self.assertEqual(len(tracks), 1)
        self.assertEqual(tracks[0]["jamendo_id"], "track-1")

    def test_recursive_scan_reads_local_file_duration(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            nested = root / "Album"
            nested.mkdir()
            track_path = nested / "short.wav"
            with wave.open(str(track_path), "wb") as audio_file:
                audio_file.setnchannels(1)
                audio_file.setsampwidth(1)
                audio_file.setframerate(8000)
                audio_file.writeframes(b"\x80" * 16000)

            tracks = scan_audio_folder(str(root))

        self.assertEqual(len(tracks), 1)
        self.assertEqual(tracks[0]["title"], "short")
        self.assertEqual(tracks[0]["duration"], 2)


if __name__ == "__main__":
    unittest.main()
