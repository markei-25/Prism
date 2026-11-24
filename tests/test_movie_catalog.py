import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtWidgets import QApplication, QScrollArea, QWidget

from ui.movie_catalog import MovieCatalogView


class MovieCatalogLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_title_and_overview_stack_below_poster_at_compact_sizes(self):
        for size in ((700, 520), (900, 650)):
            with self.subTest(size=size):
                view = MovieCatalogView("test-api-key")
                view.resize(*size)
                view.show()
                self.app.processEvents()

                details_content = view.findChild(QWidget, "details_content")
                details_scroll = view.findChild(QScrollArea, "details_scroll")
                self.assertIsNotNone(details_content)
                self.assertIsNotNone(details_scroll)
                self.assertEqual(
                    details_scroll.horizontalScrollBarPolicy(),
                    Qt.ScrollBarPolicy.ScrollBarAlwaysOff,
                )

                poster_bottom = view.poster_label.mapTo(
                    details_content, QPoint(0, view.poster_label.height())
                ).y()
                title_top = view.details_title.mapTo(
                    details_content, QPoint(0, 0)
                ).y()
                title_bottom = view.details_title.mapTo(
                    details_content, QPoint(0, view.details_title.height())
                ).y()
                overview_top = view.overview.mapTo(
                    details_content, QPoint(0, 0)
                ).y()

                self.assertLessEqual(poster_bottom, title_top)
                self.assertLessEqual(title_bottom, overview_top)
                self.assertGreaterEqual(
                    details_content.height(),
                    details_scroll.viewport().height(),
                )

                view.close()


if __name__ == "__main__":
    unittest.main()
