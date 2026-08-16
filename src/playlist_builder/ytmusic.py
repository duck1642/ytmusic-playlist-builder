from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class YtMusicError(RuntimeError):
    """Raised when a YouTube Music item cannot be resolved safely."""


@dataclass(frozen=True, slots=True)
class ArtistReference:
    requested_name: str
    display_name: str
    channel_id: str


def _normalise(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    return "".join(char for char in decomposed if not unicodedata.combining(char)).strip()


def _result_name(result: dict[str, Any]) -> str | None:
    for key in ("artist", "name", "title"):
        value = result.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _result_id(result: dict[str, Any]) -> str | None:
    for key in ("browseId", "channelId", "id"):
        value = result.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


class YtMusicAdapter:
    """Small boundary around the ytmusicapi methods used by this project."""

    def __init__(self, client: Any) -> None:
        self.client = client

    @classmethod
    def from_auth(cls, auth_file: Path | None = None) -> "YtMusicAdapter":
        try:
            from ytmusicapi import YTMusic
        except ImportError as error:
            raise YtMusicError(
                "ytmusicapi is required for live YouTube Music access; install requirements.txt"
            ) from error

        client = YTMusic(str(auth_file)) if auth_file is not None else YTMusic()
        return cls(client)

    def resolve_artist(self, name: str) -> ArtistReference:
        results = self.client.search(name, filter="artists", limit=10)
        exact_matches: dict[str, ArtistReference] = {}
        for result in results:
            if not isinstance(result, dict):
                continue
            result_type = result.get("resultType")
            if result_type is not None and str(result_type).casefold() != "artist":
                continue
            display_name = _result_name(result)
            channel_id = _result_id(result)
            if display_name is None or channel_id is None:
                continue
            if _normalise(display_name) == _normalise(name):
                exact_matches[channel_id] = ArtistReference(name, display_name, channel_id)

        if len(exact_matches) != 1:
            if not exact_matches:
                raise YtMusicError(f"No exact artist match found for: {name}")
            raise YtMusicError(f"Multiple exact artist matches found for: {name}")
        return next(iter(exact_matches.values()))

    def list_releases(self, artist: ArtistReference) -> list[dict[str, Any]]:
        artist_page = self.client.get_artist(artist.channel_id)
        releases: list[dict[str, Any]] = []
        seen_ids: set[str] = set()

        for section_name in ("albums", "singles"):
            section = artist_page.get(section_name, {})
            if not isinstance(section, dict):
                continue
            params = section.get("params")
            if isinstance(params, str) and params:
                section_id = section.get("browseId") or artist.channel_id
                section_releases = self.client.get_artist_albums(
                    section_id,
                    params,
                    limit=None,
                )
            else:
                section_releases = section.get("results", [])

            if not isinstance(section_releases, list):
                continue
            for release in section_releases:
                if not isinstance(release, dict):
                    continue
                release_id = _result_id(release)
                if release_id is None or release_id in seen_ids:
                    continue
                seen_ids.add(release_id)
                releases.append(release)
        return releases

    def get_album(self, browse_id: str) -> dict[str, Any]:
        album = self.client.get_album(browse_id)
        if not isinstance(album, dict):
            raise YtMusicError(f"Invalid album response for: {browse_id}")
        return album
