from __future__ import annotations

import re
from typing import Any

from .models import Track
from .ytmusic import ArtistReference


def _text(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _integer(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        return int(value) if value is not None and str(value).strip() else None
    except (TypeError, ValueError):
        return None


def _year(value: Any) -> int | None:
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, str):
        match = re.search(r"\b(\d{4})\b", value)
        if match:
            return int(match.group(1))
    return None


class CatalogCollector:
    """Convert ytmusicapi album responses into the project's Track model."""

    def __init__(self, api: Any) -> None:
        self.api = api
        self._artist_cache: dict[str, list[Track]] = {}

    def collect_artist(self, artist: ArtistReference) -> list[Track]:
        cached = self._artist_cache.get(artist.channel_id)
        if cached is not None:
            return list(cached)

        tracks: list[Track] = []
        for release in self.api.list_releases(artist):
            release_id = _text(release.get("browseId")) or _text(release.get("id"))
            if release_id is None:
                continue
            album = self.api.get_album(release_id)
            album_name = _text(album.get("title")) or _text(release.get("title"))
            if album_name is None:
                continue
            album_type = _text(album.get("type")) or _text(release.get("type")) or "Album"
            release_year = _year(album.get("year")) or _year(release.get("year"))
            raw_tracks = album.get("tracks", [])
            if not isinstance(raw_tracks, list):
                continue

            for raw_track in raw_tracks:
                if not isinstance(raw_track, dict):
                    continue
                video_id = _text(raw_track.get("videoId"))
                title = _text(raw_track.get("title"))
                if video_id is None or title is None:
                    continue
                tracks.append(
                    Track(
                        video_id=video_id,
                        artist=artist.display_name,
                        album=album_name,
                        title=title,
                        album_type=album_type,
                        release_year=release_year,
                        track_number=_integer(raw_track.get("trackNumber")),
                        source_artist_id=artist.channel_id,
                        album_id=release_id,
                        duration_seconds=_integer(raw_track.get("duration_seconds")),
                    )
                )
        self._artist_cache[artist.channel_id] = list(tracks)
        return tracks
