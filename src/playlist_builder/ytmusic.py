from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
from urllib.parse import unquote, urlparse


class YtMusicError(RuntimeError):
    """Raised when a YouTube Music item cannot be resolved safely."""


@dataclass(frozen=True, slots=True)
class ArtistReference:
    requested_name: str
    display_name: str
    channel_id: str


@dataclass(frozen=True, slots=True)
class ArtistInput:
    """One artist-list entry in name, URL, or name-plus-URL form."""

    raw: str
    display_name: str | None = None
    url: str | None = None
    channel_id: str | None = None
    handle: str | None = None

    @property
    def label(self) -> str:
        return self.display_name or self.handle or self.channel_id or self.raw


_YOUTUBE_HOSTS = frozenset(
    {
        "music.youtube.com",
        "www.music.youtube.com",
        "youtube.com",
        "www.youtube.com",
    }
)


def parse_artist_input(value: str) -> ArtistInput:
    """Parse a plain artist name, an artist URL, or ``name | URL``."""

    raw = value.strip()
    if not raw or raw.startswith("#"):
        raise YtMusicError("Artist input cannot be empty or a comment")

    display_name: str | None = None
    candidate = raw
    if "|" in raw:
        name_part, url_part = raw.split("|", 1)
        display_name = name_part.strip()
        candidate = url_part.strip()
        if not display_name:
            raise YtMusicError(f"Artist name is missing before '|': {raw}")
        if not candidate:
            raise YtMusicError(f"Artist URL is missing after '|': {raw}")

    if not candidate.startswith(("http://", "https://")):
        if "|" in raw:
            raise YtMusicError(f"Artist URL must be an http(s) URL: {candidate}")
        return ArtistInput(raw=raw, display_name=display_name or raw)

    parsed = urlparse(candidate)
    hostname = (parsed.hostname or "").casefold()
    if parsed.scheme not in {"http", "https"} or hostname not in _YOUTUBE_HOSTS:
        raise YtMusicError(f"Unsupported YouTube artist URL: {candidate}")

    path = unquote(parsed.path).rstrip("/")
    if path.startswith("/channel/"):
        channel_id = path.removeprefix("/channel/").strip("/")
        if not channel_id or "/" in channel_id:
            raise YtMusicError(f"YouTube channel ID is missing from URL: {candidate}")
        return ArtistInput(
            raw=raw,
            display_name=display_name,
            url=candidate,
            channel_id=channel_id,
        )

    if path.startswith("/@"):
        handle = path.removeprefix("/@").strip("/")
        if not handle or "/" in handle:
            raise YtMusicError(f"YouTube handle is missing from URL: {candidate}")
        return ArtistInput(
            raw=raw,
            display_name=display_name,
            url=candidate,
            handle=handle,
        )

    raise YtMusicError(
        "Artist URL must use /@handle or /channel/<channel-id>: "
        f"{candidate}"
    )


def normalize_artist_name(value: str) -> str:
    """Create a conservative, whitespace-normalized artist name key."""

    normalized = unicodedata.normalize("NFKC", value).casefold()
    return " ".join(normalized.split())


def canonical_artist_key(value: str | ArtistInput) -> str:
    """Return a local key for duplicate detection without network access."""

    artist_input = parse_artist_input(value) if isinstance(value, str) else value
    if artist_input.channel_id is not None:
        return f"channel:{artist_input.channel_id}"
    if artist_input.handle is not None:
        return f"handle:{artist_input.handle.casefold()}"
    return f"name:{normalize_artist_name(artist_input.display_name or artist_input.raw)}"


def _normalise(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    return "".join(char for char in decomposed if not unicodedata.combining(char)).strip()


def _handle_match_key(value: str) -> str:
    return normalize_artist_name(value).replace(" ", "")


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
        self._artist_cache: dict[str, ArtistReference] = {}

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

    def resolve_artist(self, value: str | ArtistInput) -> ArtistReference:
        artist_input = parse_artist_input(value) if isinstance(value, str) else value
        input_key = canonical_artist_key(artist_input)
        cached = self._artist_cache.get(input_key)
        if cached is not None:
            return cached

        if artist_input.channel_id is not None:
            reference = ArtistReference(
                artist_input.raw,
                artist_input.label,
                artist_input.channel_id,
            )
            return self._cache_artist_reference(reference, artist_input)

        query = artist_input.handle or artist_input.display_name or artist_input.raw
        results = self._call(
            "Artist search",
            self.client.search,
            query,
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
            if artist_input.handle is not None:
                matches = _handle_match_key(display_name) == _handle_match_key(query)
            else:
                matches = _normalise(display_name) == _normalise(query)
            if matches:
                exact_matches[channel_id] = ArtistReference(
                    artist_input.raw,
                    artist_input.display_name or display_name,
                    channel_id,
                )

        if len(exact_matches) != 1:
            if not exact_matches:
                raise YtMusicError(f"No exact artist match found for: {query}")
            raise YtMusicError(f"Multiple exact artist matches found for: {query}")
        return self._cache_artist_reference(next(iter(exact_matches.values())), artist_input)

    def _cache_artist_reference(
        self,
        reference: ArtistReference,
        artist_input: ArtistInput,
    ) -> ArtistReference:
        keys = {
            canonical_artist_key(artist_input),
            f"channel:{reference.channel_id}",
            f"name:{normalize_artist_name(reference.display_name)}",
        }
        if artist_input.handle is not None:
            keys.add(f"handle:{artist_input.handle.casefold()}")
        for key in keys:
            self._artist_cache[key] = reference
        return reference

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
