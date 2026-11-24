import os
import time
import unittest
import weakref
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "test-anon-key")

from postgrest.exceptions import APIError
from PyQt6.QtCore import QThread, Qt, QTimer, pyqtSlot
from PyQt6.QtWidgets import QMainWindow
from PyQt6.QtWidgets import QApplication

from ui.main_window import MainWindow, MusicLibraryLoader


class DelayedWorker(QThread):
    def run(self):
        self.msleep(200)


class WorkerOwner(QMainWindow):
    def __init__(self):
        super().__init__()
        self._background_workers = {}

    @pyqtSlot()
    def _release_background_worker(self):
        worker = self.sender()
        worker_id = id(worker)
        QTimer.singleShot(
            0,
            lambda retained_id=worker_id: self._dispose_background_worker(
                retained_id
            ),
        )

    def _dispose_background_worker(self, worker_id):
        worker = self._background_workers.pop(worker_id, None)
        if worker is not None:
            worker.wait()
            worker.deleteLater()


class MusicLibraryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_missing_supabase_tables_report_setup_instructions(self):
        worker = MusicLibraryLoader(7, "user-1", liked_only=False)
        failures = []
        worker.failed.connect(lambda request_id, message: failures.append((request_id, message)))
        error = APIError(
            {
                "code": "PGRST205",
                "message": "Could not find the table 'public.songs' in the schema cache",
                "details": None,
                "hint": None,
            }
        )

        with self.assertLogs("ui.main_window", level="ERROR"):
            with patch("ui.main_window.db.fetch_all_songs", side_effect=error):
                worker.run()

        self.assertEqual(failures[0][0], 7)
        self.assertIn("202611060001_legacy_music_library.sql", failures[0][1])
        self.assertIn("Jamendo and Local files", failures[0][1])

    def test_background_worker_is_retained_until_it_finishes(self):
        owner = WorkerOwner()
        worker = DelayedWorker()
        worker_reference = weakref.ref(worker)

        MainWindow._retain_background_worker(owner, worker)
        worker.start()
        del worker

        retained = worker_reference()
        self.assertIsNotNone(retained)
        self.assertTrue(retained.isRunning())
        del retained

        deadline = time.monotonic() + 1
        while owner._background_workers and time.monotonic() < deadline:
            self.app.processEvents()
            time.sleep(0.01)

        self.assertFalse(owner._background_workers)
        owner.close()


if __name__ == "__main__":
    unittest.main()
