import unittest
from unittest.mock import patch

from ui.music_queue import PlaybackQueue


def tracks(count):
    return [{"title": f"Track {index}"} for index in range(count)]


class PlaybackQueueTests(unittest.TestCase):
    def test_sequential_queue_stops_or_wraps_by_repeat_mode(self):
        queue = PlaybackQueue()
        queue.replace(tracks(2), 0)

        self.assertEqual(queue.next_index(), 1)
        self.assertIsNone(queue.next_index())

        queue.repeat_mode = "all"
        self.assertEqual(queue.next_index(), 0)

    def test_repeat_one_replays_current_track(self):
        queue = PlaybackQueue()
        queue.replace(tracks(2), 1)
        queue.repeat_mode = "one"

        self.assertEqual(queue.next_index(), 1)

    def test_shuffle_visits_each_track_once_before_stopping(self):
        queue = PlaybackQueue()
        queue.replace(tracks(4), 0)
        queue.shuffle_enabled = True

        with patch("ui.music_queue.random.choice", side_effect=lambda options: options[-1]):
            self.assertEqual(queue.next_index(), 3)
            self.assertEqual(queue.next_index(), 2)
            self.assertEqual(queue.next_index(), 1)
        self.assertIsNone(queue.next_index())

    def test_shuffle_repeat_all_starts_a_new_cycle(self):
        queue = PlaybackQueue()
        queue.replace(tracks(2), 0)
        queue.shuffle_enabled = True
        queue.repeat_mode = "all"

        with patch("ui.music_queue.random.choice", side_effect=lambda options: options[0]):
            self.assertEqual(queue.next_index(), 1)
            self.assertEqual(queue.next_index(), 0)

    def test_shuffle_repeat_all_repeats_a_single_track(self):
        queue = PlaybackQueue()
        queue.replace(tracks(1), 0)
        queue.shuffle_enabled = True
        queue.repeat_mode = "all"

        self.assertEqual(queue.next_index(), 0)

    def test_previous_replays_current_after_five_seconds_then_uses_history(self):
        queue = PlaybackQueue()
        queue.replace(tracks(3), 0)
        queue.play_index(1)
        queue.play_index(2)

        self.assertEqual(queue.previous_index(7), 2)
        self.assertEqual(queue.previous_index(0), 1)

    def test_queue_removal_preserves_current_track_and_indices(self):
        queue = PlaybackQueue()
        queue.replace(tracks(3), 2)

        self.assertFalse(queue.remove(2))
        self.assertTrue(queue.remove(0))
        self.assertEqual(queue.current_index, 1)
        self.assertEqual(queue.tracks[1]["title"], "Track 2")


if __name__ == "__main__":
    unittest.main()
