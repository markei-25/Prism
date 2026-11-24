import json
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from ui.archive_api import (
    ArchiveAPIError,
    fetch_archive_movie,
    license_allows_playback,
    search_archive_movies,
)


class ArchiveAPITests(unittest.TestCase):
    def _mock_response(self, payload):
        patcher = patch("ui.archive_api.urlopen")
        request = patcher.start()
        self.addCleanup(patcher.stop)
        request.return_value.__enter__.return_value.read.return_value = json.dumps(
            payload
        ).encode("utf-8")
        return request

    def test_search_scopes_to_feature_films_and_sanitizes_title(self):
        request = self._mock_response(
            {
                "response": {
                    "docs": [
                        {
                            "identifier": "frankenstein-1931",
                            "title": "Frankenstein",
                            "year": 1931,
                            "licenseurl": "https://creativecommons.org/publicdomain/mark/1.0/",
                        }
                    ]
                }
            }
        )

        results = search_archive_movies('Frankenstein" AND mediatype:audio')

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].identifier, "frankenstein-1931")
        query = parse_qs(urlsplit(request.call_args.args[0].full_url).query)
        self.assertIn("collection:feature_films", query["q"][0])
        self.assertIn("mediatype:movies", query["q"][0])
        self.assertIn('title:"Frankenstein AND mediatype audio"', query["q"][0])

    def test_search_rejects_empty_or_only_operators(self):
        with self.assertRaises(ArchiveAPIError):
            search_archive_movies(" : / ? ")

    def test_fetch_uses_supported_license_and_h264_derivative(self):
        self._mock_response(
            {
                "metadata": {
                    "identifier": "frankenstein-1931",
                    "mediatype": "movies",
                    "title": "Frankenstein",
                    "year": "1931",
                    "licenseurl": "http://creativecommons.org/publicdomain/mark/1.0/",
                },
                "files": [
                    {
                        "name": "source.mkv",
                        "format": "Matroska",
                        "source": "original",
                    },
                    {
                        "name": "Frankenstein (1931).mp4",
                        "format": "h.264",
                        "source": "derivative",
                    },
                ],
            }
        )

        movie = fetch_archive_movie("frankenstein-1931")

        self.assertEqual(
            movie.stream_url,
            "https://archive.org/download/frankenstein-1931/"
            "Frankenstein%20%281931%29.mp4",
        )
        self.assertTrue(license_allows_playback(movie.license_url))

    def test_fetch_does_not_enable_playback_without_supported_license(self):
        self._mock_response(
            {
                "metadata": {
                    "identifier": "unlicensed-film",
                    "mediatype": "movies",
                    "title": "Film",
                },
                "files": [
                    {"name": "film.mp4", "format": "h.264", "source": "derivative"}
                ],
            }
        )

        movie = fetch_archive_movie("unlicensed-film")

        self.assertIsNone(movie.stream_url)
        self.assertFalse(license_allows_playback(movie.license_url))

    def test_fetch_ignores_private_and_path_traversal_files(self):
        self._mock_response(
            {
                "metadata": {
                    "identifier": "safe-item",
                    "mediatype": "movies",
                    "title": "Film",
                    "licenseurl": "https://creativecommons.org/licenses/by/4.0/",
                },
                "files": [
                    {
                        "name": "../film.mp4",
                        "format": "h.264",
                        "source": "derivative",
                    },
                    {
                        "name": "private.mp4",
                        "format": "h.264",
                        "source": "derivative",
                        "private": "true",
                    },
                ],
            }
        )

        movie = fetch_archive_movie("safe-item")

        self.assertIsNone(movie.stream_url)


if __name__ == "__main__":
    unittest.main()
