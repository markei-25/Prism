# player.py
"""Prism audio playback engine using pygame-ce."""

import io
import urllib.request
import pygame

class AudioPlayer:
    def __init__(self):
        pygame.mixer.init()
        self.current_song: dict | None = None
        self.is_paused: bool = False
        self.volume: float = 0.7
        pygame.mixer.music.set_volume(self.volume)

    def play_url(self, audio_url: str, song_data: dict = None) -> bool:
        """Fetches audio over HTTPS and feeds the stream to pygame.mixer."""
        try:
            req = urllib.request.Request(
                audio_url,
                headers={'User-Agent': 'Mozilla/5.0'}
            )
            with urllib.request.urlopen(req) as response:
                audio_bytes = io.BytesIO(response.read())

            pygame.mixer.music.load(audio_bytes)
            pygame.mixer.music.play()
            self.current_song = song_data
            self.is_paused = False
            return True
        except Exception as err:
            print(f"Audio engine playback error: {err}")
            return False

    def pause(self):
        """Pauses currently playing track."""
        if pygame.mixer.music.get_busy() and not self.is_paused:
            pygame.mixer.music.pause()
            self.is_paused = True

    def resume(self):
        """Resumes track if paused."""
        if self.is_paused:
            pygame.mixer.music.unpause()
            self.is_paused = False

    def stop(self):
        """Stops active audio playback."""
        pygame.mixer.music.stop()
        self.current_song = None
        self.is_paused = False

    def set_volume(self, value: int):
        """Sets volume level (0 to 100)."""
        self.volume = max(0.0, min(1.0, value / 100.0))
        pygame.mixer.music.set_volume(self.volume)

    def is_playing(self) -> bool:
        """Returns True if music is actively playing."""
        return pygame.mixer.music.get_busy() and not self.is_paused