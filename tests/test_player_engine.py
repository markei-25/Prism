import unittest
from unittest.mock import patch

import pygame

from player import AudioPlayer


class AudioPlayerPositionTests(unittest.TestCase):
    def test_position_tracks_elapsed_time_and_seek_offset(self):
        clock = [100.0]
        with (
            patch("player.pygame.mixer.init"),
            patch("player.pygame.mixer.music.set_volume"),
            patch("player.pygame.mixer.music.get_busy", return_value=True),
            patch("player.pygame.mixer.music.set_pos") as set_pos,
            patch("player.pygame.mixer.music.pause"),
            patch("player.pygame.mixer.music.unpause"),
            patch("player.time.monotonic", side_effect=lambda: clock[0]),
        ):
            player = AudioPlayer()
            player.current_song = {"duration": 60}

            clock[0] += 2
            self.assertEqual(player.position_seconds(), 2)

            self.assertTrue(player.seek(30))
            set_pos.assert_called_once_with(30)
            clock[0] += 3
            self.assertEqual(player.position_seconds(), 33)

            player.pause()
            clock[0] += 5
            self.assertEqual(player.position_seconds(), 33)
            player.resume()
            clock[0] += 2
            self.assertEqual(player.position_seconds(), 35)

    def test_seek_reports_format_errors(self):
        with (
            patch("player.pygame.mixer.init"),
            patch("player.pygame.mixer.music.set_volume"),
            patch(
                "player.pygame.mixer.music.set_pos",
                side_effect=pygame.error("unsupported"),
            ),
            patch("player.LOGGER.exception"),
        ):
            player = AudioPlayer()
            player.current_song = {"duration": 60}

            self.assertFalse(player.seek(10))


if __name__ == "__main__":
    unittest.main()
