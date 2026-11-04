"""Background tasks for catalog search, local scans, and audio loading."""

import logging
import urllib.error
import urllib.request

from PyQt6.QtCore import QThread, pyqtSignal

from ui.music_sources import scan_audio_folder, search_jamendo_tracks

LOGGER = logging.getLogger(__name__)


class DatabaseWorker(QThread):
    result_ready = pyqtSignal(int, object)
    failed = pyqtSignal(int, str)

    def __init__(self, request_id: int, operation):
        super().__init__()
        self.request_id = request_id
        self.operation = operation

    def run(self):
        try:
            result = self.operation()
        except Exception as error:
            LOGGER.exception("Prism playlist database operation failed")
            self.failed.emit(self.request_id, str(error))
            return
        self.result_ready.emit(self.request_id, result)


class JamendoSearchWorker(QThread):
    loaded = pyqtSignal(int, list)
    failed = pyqtSignal(int, str)

    def __init__(self, request_id: int, client_id: str, query: str, genre: str):
        super().__init__()
        self.request_id = request_id
        self.client_id = client_id
        self.query = query
        self.genre = genre

    def run(self):
        try:
            tracks = search_jamendo_tracks(self.client_id, self.query, self.genre)
        except RuntimeError as error:
            self.failed.emit(self.request_id, str(error))
            return
        self.loaded.emit(self.request_id, tracks)


class LocalFolderScanWorker(QThread):
    loaded = pyqtSignal(int, list)
    failed = pyqtSignal(int, str)

    def __init__(self, request_id: int, folder: str):
        super().__init__()
        self.request_id = request_id
        self.folder = folder

    def run(self):
        try:
            tracks = scan_audio_folder(self.folder)
        except RuntimeError as error:
            self.failed.emit(self.request_id, str(error))
            return
        self.loaded.emit(self.request_id, tracks)


class AudioDownloadWorker(QThread):
    loaded = pyqtSignal(int, dict, bytes)
    failed = pyqtSignal(int, str)

    MAX_AUDIO_BYTES = 50_000_000

    def __init__(self, request_id: int, track: dict):
        super().__init__()
        self.request_id = request_id
        self.track = track

    def run(self):
        audio_url = str(self.track.get("audio_url") or "")
        if not audio_url.startswith("https://"):
            self.failed.emit(self.request_id, "The track does not have a secure audio stream.")
            return

        request = urllib.request.Request(
            audio_url,
            headers={"User-Agent": "PrismMediaHub/1.0"},
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                audio_data = response.read(self.MAX_AUDIO_BYTES + 1)
        except urllib.error.HTTPError as error:
            self.failed.emit(
                self.request_id,
                f"The audio source returned HTTP {error.code}.",
            )
            return
        except urllib.error.URLError:
            self.failed.emit(
                self.request_id,
                "Could not load this audio stream. Check your internet connection.",
            )
            return
        except OSError as error:
            self.failed.emit(self.request_id, f"Could not load this audio file: {error}")
            return

        if len(audio_data) > self.MAX_AUDIO_BYTES:
            self.failed.emit(self.request_id, "This audio stream is too large to load.")
            return
        self.loaded.emit(self.request_id, self.track, audio_data)
