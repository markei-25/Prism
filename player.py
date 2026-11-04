# player.py
"""Prism audio playback engine using pygame-ce."""

import io
import logging
import time
import urllib.request
import pygame


LOGGER = logging.getLogger(__name__)


class AudioPlayer:
    def __init__(self):
        pygame.mixer.init()
        self.current_song: dict | None = None
        self.is_paused: bool = False
        self.volume: float = 0.7
        self._position_seconds = 0.0
        self._position_updated_at = time.monotonic()
        pygame.mixer.music.set_volume(self.volume)

    def play_url(self, audio_url: str, song_data: dict = None) -> bool:
        """Fetches audio over HTTPS and feeds the stream to pygame.mixer."""
        try:
            req = urllib.request.Request(
                audio_url,
                headers={'User-Agent': 'Mozilla/5.0'}
            )
            with urllib.request.urlopen(req, timeout=30) as response:
                return self.play_bytes(response.read(), song_data)
        except (OSError, pygame.error) as err:
            LOGGER.exception("Audio engine URL playback failed")
            return False

    def play_bytes(self, audio_bytes: bytes, song_data: dict | None = None) -> bool:
        """Starts playback from downloaded audio bytes."""
        try:
            pygame.mixer.music.load(io.BytesIO(audio_bytes))
            pygame.mixer.music.play()
            self.current_song = song_data
            self.is_paused = False
            self._reset_position()
            return True
        except (OSError, pygame.error, ValueError):
            LOGGER.exception("Audio engine could not decode downloaded audio")
            return False

    def play_file(self, file_path: str, song_data: dict | None = None) -> bool:
        """Starts playback directly from a local audio file."""
        try:
            pygame.mixer.music.load(file_path)
            pygame.mixer.music.play()
            self.current_song = song_data
            self.is_paused = False
            self._reset_position()
            return True
        except (OSError, pygame.error, ValueError):
            LOGGER.exception("Audio engine could not play local audio file")
            return False

    def pause(self):
        """Pauses currently playing track."""
        if pygame.mixer.music.get_busy() and not self.is_paused:
            self._sync_position()
            pygame.mixer.music.pause()
            self.is_paused = True

    def resume(self):
        """Resumes track if paused."""
        if self.is_paused:
            self._position_updated_at = time.monotonic()
            pygame.mixer.music.unpause()
            self.is_paused = False

    def stop(self):
        """Stops active audio playback."""
        pygame.mixer.music.stop()
        pygame.mixer.music.unload()
        self.current_song = None
        self.is_paused = False
        self._reset_position()

    def position_seconds(self) -> float:
        """Returns the current playback position in seconds."""
        self._sync_position()
        return self._position_seconds

    def seek(self, position_seconds: int) -> bool:
        """Seeks to a track position when the active audio format supports it."""
        if not self.current_song:
            return False
        duration = max(0, int(self.current_song.get("duration") or 0))
        if duration <= 0:
            return False
        position = max(0, min(duration, int(position_seconds)))
        try:
            pygame.mixer.music.set_pos(position)
        except (pygame.error, ValueError):
            LOGGER.exception("Audio engine could not seek in the active track")
            return False
        self._position_seconds = float(position)
        self._position_updated_at = time.monotonic()
        return True

    def _sync_position(self):
        now = time.monotonic()
        if (
            self.current_song
            and not self.is_paused
            and pygame.mixer.music.get_busy()
        ):
            self._position_seconds += max(0.0, now - self._position_updated_at)
            duration = max(0, int(self.current_song.get("duration") or 0))
            if duration:
                self._position_seconds = min(self._position_seconds, duration)
        self._position_updated_at = now

    def _reset_position(self):
        self._position_seconds = 0.0
        self._position_updated_at = time.monotonic()

    def set_volume(self, value: int):
        """Sets volume level (0 to 100)."""
        self.volume = max(0.0, min(1.0, value / 100.0))
        pygame.mixer.music.set_volume(self.volume)

    def is_playing(self) -> bool:
        """Returns True if music is actively playing."""
        return pygame.mixer.music.get_busy() and not self.is_paused