"""Playback queue state independent of the Qt interface."""

import random


class PlaybackQueue:
    def __init__(self):
        self.tracks: list[dict] = []
        self.current_index = -1
        self.shuffle_enabled = False
        self.repeat_mode = "off"
        self._played_indices: set[int] = set()
        self._history: list[int] = []

    def replace(self, tracks: list[dict], index: int) -> None:
        if not tracks or not 0 <= index < len(tracks):
            raise IndexError("The selected track is not in the queue.")
        self.tracks = list(tracks)
        self.current_index = index
        self._played_indices = {index}
        self._history.clear()

    def add(self, track: dict) -> int:
        self.tracks.append(track)
        if self.current_index < 0:
            self.current_index = 0
            self._played_indices = {0}
        return len(self.tracks) - 1

    def play_index(self, index: int) -> int:
        if not 0 <= index < len(self.tracks):
            raise IndexError("The selected track is not in the queue.")
        if self.current_index >= 0 and index != self.current_index:
            self._history.append(self.current_index)
        self.current_index = index
        self._played_indices.add(index)
        return index

    def next_index(self) -> int | None:
        if not self.tracks or self.current_index < 0:
            return None
        if self.repeat_mode == "one":
            return self.current_index

        if self.shuffle_enabled:
            candidates = [
                index
                for index in range(len(self.tracks))
                if index not in self._played_indices
            ]
            if not candidates and self.repeat_mode == "all":
                self._played_indices = {self.current_index}
                candidates = [
                    index
                    for index in range(len(self.tracks))
                    if index not in self._played_indices
                ]
                if not candidates:
                    return self.current_index
            if not candidates:
                return None
            next_index = random.choice(candidates)
        else:
            next_index = self.current_index + 1
            if next_index >= len(self.tracks):
                if self.repeat_mode != "all":
                    return None
                next_index = 0

        self._history.append(self.current_index)
        self.current_index = next_index
        self._played_indices.add(next_index)
        return next_index

    def previous_index(self, position_seconds: float) -> int | None:
        if not self.tracks or self.current_index < 0:
            return None
        if position_seconds > 5:
            return self.current_index
        if not self._history:
            return self.current_index
        self.current_index = self._history.pop()
        self._played_indices.add(self.current_index)
        return self.current_index

    def remove(self, index: int) -> bool:
        if not 0 <= index < len(self.tracks) or index == self.current_index:
            return False
        del self.tracks[index]
        self._played_indices = {
            played - 1 if played > index else played
            for played in self._played_indices
            if played != index
        }
        self._history = [
            played - 1 if played > index else played
            for played in self._history
            if played != index
        ]
        if index < self.current_index:
            self.current_index -= 1
        return True

    def clear(self) -> None:
        self.tracks.clear()
        self.current_index = -1
        self._played_indices.clear()
        self._history.clear()
