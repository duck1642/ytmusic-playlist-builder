from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


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

    @staticmethod
    def _call(operation: str, callback: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        try:
            return callback(*args, **kwargs)
        except YtMusicError:
            raise
        except Exception as error:
            raise YtMusicError(f"{operation} failed: {error}") from error

    @classmethod
    def from_auth(
        cls,
        auth_file: Path | None = None,
        *,
        oauth_client_file: Path | None = None,
    ) -> "YtMusicAdapter":
        try:
            from ytmusicapi import YTMusic
        except ImportError as error:
            raise YtMusicError(
                "ytmusicapi is required for live YouTube Music access; install requirements.txt"
            ) from error

        from .network import create_requests_session

        session = create_requests_session()
        if auth_file is None:
            client = YTMusic(requests_session=session)
        elif oauth_client_file is None:
            client = YTMusic(str(auth_file), requests_session=session)
        else:
            from .auth import load_oauth_client

            try:
                from ytmusicapi.auth.oauth import OAuthCredentials
            except ImportError as error:
                raise YtMusicError("ytmusicapi OAuth support is unavailable") from error
            try:
                oauth_client = load_oauth_client(oauth_client_file)
            except OSError as error:
                raise YtMusicError(f"Could not read OAuth client file: {error}") from error
            except RuntimeError as error:
                raise YtMusicError(str(error)) from error
            credentials = OAuthCredentials(
                oauth_client.client_id,
                oauth_client.client_secret,
                session=session,
            )
            client = YTMusic(
                str(auth_file),
                requests_session=session,
                oauth_credentials=credentials,
            )
        return cls(client)

    def resolve_artist(self, name: str) -> ArtistReference:
        results = self._call(
            "Artist search",
            self.client.search,
            name,
            filter="artists",
            limit=10,
        )
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
        artist_page = self._call("Artist lookup", self.client.get_artist, artist.channel_id)
        if not isinstance(artist_page, dict):
            raise YtMusicError(f"Invalid artist response for: {artist.channel_id}")
        releases: list[dict[str, Any]] = []
        seen_ids: set[str] = set()

        for section_name in ("albums", "singles"):
            section = artist_page.get(section_name, {})
            if not isinstance(section, dict):
                continue
            params = section.get("params")
            if isinstance(params, str) and params:
                section_id = section.get("browseId") or artist.channel_id
                section_releases = self._call(
                    "Release lookup",
                    self.client.get_artist_albums,
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
        album = self._call("Album lookup", self.client.get_album, browse_id)
        if not isinstance(album, dict):
            raise YtMusicError(f"Invalid album response for: {browse_id}")
        return album

    def list_playlists(self) -> list[dict[str, Any]]:
        playlists = self._call(
            "Playlist list lookup",
            self.client.get_library_playlists,
            limit=None,
        )
        if not isinstance(playlists, list):
            raise YtMusicError("Invalid playlist list response")
        return [playlist for playlist in playlists if isinstance(playlist, dict)]

    def get_playlist_video_ids(self, playlist_id: str) -> list[str]:
        playlist = self._call(
            "Playlist lookup",
            self.client.get_playlist,
            playlist_id,
            limit=None,
        )
        if not isinstance(playlist, dict):
            raise YtMusicError(f"Invalid playlist response for: {playlist_id}")
        tracks = playlist.get("tracks", [])
        if not isinstance(tracks, list):
            return []
        return [
            video_id
            for track in tracks
            if isinstance(track, dict)
            for video_id in [track.get("videoId")]
            if isinstance(video_id, str) and video_id
        ]

    def create_playlist(
        self,
        title: str,
        description: str,
        privacy: str,
        video_ids: list[str],
    ) -> str:
        result = self._call(
            "Playlist creation",
            self.client.create_playlist,
            title,
            description,
            privacy_status=privacy,
            video_ids=video_ids or None,
        )
        if not isinstance(result, str) or not result:
            raise YtMusicError(f"Playlist creation failed for: {title}")
        return result

    def add_playlist_items(self, playlist_id: str, video_ids: list[str]) -> Any:
        result = self._call(
            "Playlist update",
            self.client.add_playlist_items,
            playlist_id,
            videoIds=video_ids,
            duplicates=False,
        )
        if isinstance(result, dict) and result.get("error"):
            raise YtMusicError(f"Could not add items to playlist: {playlist_id}")
        return result
