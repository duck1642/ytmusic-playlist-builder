from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Sequence

from .models import Track
from .state import BuildState


@dataclass(frozen=True, slots=True)
class PlaylistReport:
    title: str
    playlist_id: str | None
    created: bool
    added_video_ids: tuple[str, ...]
    skipped_video_ids: tuple[str, ...]
    manually_removed_video_ids: tuple[str, ...]


def genre_label(genre: str) -> str:
    return genre


def playlist_title(genre: str, part_number: int, part_count: int) -> str:
    base = genre_label(genre)
    return base if part_count == 1 else f"{base} {part_number}"


def _unique(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


class PlaylistWriter:
    """Create or append to RAW playlists without reconciling manual removals."""

    def __init__(self, api: Any) -> None:
        self.api = api

    def sync_genre(
        self,
        genre: str,
        chunks: Sequence[Sequence[Track]],
        state: BuildState,
        *,
        privacy: str = "PRIVATE",
        dry_run: bool = False,
    ) -> list[PlaylistReport]:
        reports: list[PlaylistReport] = []
        part_count = len(chunks)
        for index, tracks in enumerate(chunks, start=1):
            reports.append(
                self.sync_playlist(
                    playlist_title(genre, index, part_count),
                    tracks,
                    state,
                    description=f"RAW playlist for {genre_label(genre)}",
                    privacy=privacy,
                    dry_run=dry_run,
                )
            )
        return reports

    def sync_playlist(
        self,
        title: str,
        tracks: Sequence[Track],
        state: BuildState,
        *,
        description: str | None = None,
        privacy: str,
        dry_run: bool = False,
    ) -> PlaylistReport:
        desired_ids = _unique(track.video_id for track in tracks)
        previous_generated = _unique(state.generated_video_ids.get(title, []))
        removed_ids = _unique(state.removed_video_ids.get(title, []))
        playlist_id = self._find_playlist_id(title)
        created = False

        current_ids = self.api.get_playlist_video_ids(playlist_id) if playlist_id else []
        current_set = set(current_ids)

        if playlist_id is not None and not dry_run:
            state.playlist_ids[title] = playlist_id

        manually_removed = [
            video_id for video_id in previous_generated if video_id not in current_set
        ]
        removed_ids = _unique([*removed_ids, *manually_removed])
        eligible_ids = [video_id for video_id in desired_ids if video_id not in set(removed_ids)]
        skipped_ids = [video_id for video_id in desired_ids if video_id in current_set or video_id in set(removed_ids)]
        added_ids = [video_id for video_id in eligible_ids if video_id not in current_set]

        if playlist_id is None:
            created = True
            if not dry_run:
                playlist_id = self.api.create_playlist(
                    title,
                    description or f"RAW playlist for {title}",
                    privacy,
                    eligible_ids,
                )
                state.playlist_ids[title] = playlist_id
        elif added_ids and not dry_run:
            self.api.add_playlist_items(playlist_id, added_ids)

        if not dry_run:
            generated_candidates = [*previous_generated, *desired_ids]
            generated_ids = [
                video_id
                for video_id in _unique(generated_candidates)
                if video_id not in set(removed_ids)
                and (video_id in current_set or video_id in added_ids or created)
            ]
            state.generated_video_ids[title] = generated_ids
            state.removed_video_ids[title] = removed_ids

        return PlaylistReport(
            title=title,
            playlist_id=playlist_id,
            created=created,
            added_video_ids=tuple(added_ids),
            skipped_video_ids=tuple(skipped_ids),
            manually_removed_video_ids=tuple(manually_removed),
        )

    def _find_playlist_id(self, title: str) -> str | None:
        for playlist in self.api.list_playlists():
            if playlist.get("title") != title:
                continue
            playlist_id = playlist.get("playlistId") or playlist.get("id")
            if isinstance(playlist_id, str) and playlist_id:
                return playlist_id
        return None
