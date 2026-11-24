"""Internet Archive search and metadata helpers for feature films."""

import json
import re
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlsplit
from urllib.request import Request, urlopen


ARCHIVE_SEARCH_URL = "https://archive.org/advancedsearch.php"
ARCHIVE_METADATA_URL = "https://archive.org/metadata"
ARCHIVE_DOWNLOAD_URL = "https://archive.org/download"
ARCHIVE_DETAILS_URL = "https://archive.org/details"
MAX_RESULTS = 20
MAX_RESPONSE_BYTES = 8 * 1024 * 1024

_SUPPORTED_LICENSES = {
    ("creativecommons.org", "/publicdomain/mark/1.0"): "Public Domain Mark 1.0",
    ("creativecommons.org", "/publicdomain/zero/1.0"): "CC0 1.0",
    ("creativecommons.org", "/licenses/by/3.0"): "CC BY 3.0",
    ("creativecommons.org", "/licenses/by/4.0"): "CC BY 4.0",
    ("creativecommons.org", "/licenses/by-sa/3.0"): "CC BY-SA 3.0",
    ("creativecommons.org", "/licenses/by-sa/4.0"): "CC BY-SA 4.0",
}


class ArchiveAPIError(RuntimeError):
    """A user-safe Internet Archive request or response error."""


@dataclass(frozen=True)
class ArchiveSearchResult:
    identifier: str
    title: str
    year: str
    description: str
    license_url: str


@dataclass(frozen=True)
class ArchiveMovie:
    identifier: str
    title: str
    year: str
    description: str
    license_url: str
    archive_url: str
    stream_url: str | None


def _request_json(url: str) -> dict:
    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "PrismMediaHub/1.0 (Internet Archive movie browser)",
        },
    )
    try:
        with urlopen(request, timeout=15) as response:
            response_body = response.read(MAX_RESPONSE_BYTES + 1)
            if len(response_body) > MAX_RESPONSE_BYTES:
                raise ArchiveAPIError(
                    "Internet Archive returned a response that was too large."
                )
            payload = json.loads(response_body.decode("utf-8"))
    except HTTPError as error:
        raise ArchiveAPIError(
            f"Internet Archive returned HTTP {error.code}."
        ) from error
    except (URLError, TimeoutError, OSError) as error:
        raise ArchiveAPIError(
            "Could not reach Internet Archive. Check your connection and try again."
        ) from error
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ArchiveAPIError(
            "Internet Archive returned data Prism could not read."
        ) from error

    if not isinstance(payload, dict):
        raise ArchiveAPIError("Internet Archive returned an unexpected response.")
    return payload


def _first_string(value) -> str:
    if isinstance(value, list):
        value = value[0] if value else ""
    if isinstance(value, (str, int, float)):
        return str(value).strip()
    return ""


def _clean_search_text(query: str) -> str:
    text = re.sub(r"[^\w\s'-]", " ", query, flags=re.UNICODE)
    return " ".join(text.split())[:100]


def _valid_identifier(identifier: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,199}", identifier))


def _license_key(license_url: str) -> tuple[str, str] | None:
    try:
        parsed = urlsplit(license_url.strip())
    except ValueError:
        return None
    if parsed.scheme.casefold() not in ("http", "https"):
        return None
    host = parsed.hostname.casefold() if parsed.hostname else ""
    path = parsed.path.rstrip("/").casefold()
    return host, path


def license_name(license_url: str) -> str:
    key = _license_key(license_url)
    if key is None:
        return "No license listed by Internet Archive"
    return _SUPPORTED_LICENSES.get(key, "Other license listed by Internet Archive")


def license_allows_playback(license_url: str) -> bool:
    return _license_key(license_url) in _SUPPORTED_LICENSES


def search_archive_movies(query: str) -> list[ArchiveSearchResult]:
    title_query = _clean_search_text(query)
    if not title_query:
        raise ArchiveAPIError("Enter a film title to search Internet Archive.")

    archive_query = (
        "collection:feature_films AND mediatype:movies AND licenseurl:* "
        f'AND title:"{title_query}"'
    )
    parameters = [
        ("q", archive_query),
        ("fl[]", "identifier"),
        ("fl[]", "title"),
        ("fl[]", "year"),
        ("fl[]", "description"),
        ("fl[]", "licenseurl"),
        ("rows", str(MAX_RESULTS)),
        ("page", "1"),
        ("output", "json"),
    ]
    payload = _request_json(f"{ARCHIVE_SEARCH_URL}?{urlencode(parameters)}")
    response = payload.get("response")
    docs = response.get("docs") if isinstance(response, dict) else None
    if not isinstance(docs, list):
        raise ArchiveAPIError("Internet Archive returned an unexpected search result.")

    results = []
    for doc in docs:
        if not isinstance(doc, dict):
            continue
        identifier = _first_string(doc.get("identifier"))
        title = _first_string(doc.get("title"))
        if not _valid_identifier(identifier) or not title:
            continue
        results.append(
            ArchiveSearchResult(
                identifier=identifier,
                title=title,
                year=_first_string(doc.get("year")),
                description=_first_string(doc.get("description")),
                license_url=_first_string(doc.get("licenseurl")),
            )
        )
    return results[:MAX_RESULTS]


def _is_private(file_entry: dict) -> bool:
    return str(file_entry.get("private", "")).casefold() in ("1", "true", "yes")


def _mp4_file(files: list) -> str | None:
    candidates = []
    for entry in files:
        if not isinstance(entry, dict) or _is_private(entry):
            continue
        name = _first_string(entry.get("name"))
        if not name or any(part in (".", "..") for part in name.replace("\\", "/").split("/")):
            continue
        if not name.casefold().endswith(".mp4"):
            continue
        file_format = _first_string(entry.get("format")).casefold()
        if file_format not in ("h.264", "mpeg4", "mpeg-4"):
            continue
        source = _first_string(entry.get("source")).casefold()
        candidates.append((source != "derivative", file_format != "h.264", name))
    if not candidates:
        return None
    return min(candidates)[2]


def fetch_archive_movie(identifier: str) -> ArchiveMovie:
    if not _valid_identifier(identifier):
        raise ArchiveAPIError("Internet Archive returned an invalid item identifier.")

    payload = _request_json(
        f"{ARCHIVE_METADATA_URL}/{quote(identifier, safe='')}"
    )
    metadata = payload.get("metadata")
    files = payload.get("files")
    if not isinstance(metadata, dict) or not isinstance(files, list):
        raise ArchiveAPIError("Internet Archive returned incomplete film details.")
    if (
        _first_string(metadata.get("identifier")) != identifier
        or _first_string(metadata.get("mediatype")) != "movies"
    ):
        raise ArchiveAPIError("This Internet Archive item is not a movie.")

    license_url = _first_string(metadata.get("licenseurl"))
    stream_url = None
    if license_allows_playback(license_url):
        file_name = _mp4_file(files)
        if file_name:
            stream_url = (
                f"{ARCHIVE_DOWNLOAD_URL}/{quote(identifier, safe='')}/"
                f"{quote(file_name, safe='/')}"
            )

    return ArchiveMovie(
        identifier=identifier,
        title=_first_string(metadata.get("title")) or identifier,
        year=_first_string(metadata.get("year")),
        description=_first_string(metadata.get("description")),
        license_url=license_url,
        archive_url=f"{ARCHIVE_DETAILS_URL}/{quote(identifier, safe='')}",
        stream_url=stream_url,
    )
