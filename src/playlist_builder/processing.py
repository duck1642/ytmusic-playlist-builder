from __future__ import annotations

import unicodedata
from datetime import date
from typing import Iterable, Sequence

from .models import Track


def _sort_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.casefold())
    return "".join(character for character in normalized if not unicodedata.combining(character))


def _release_key(track: Track) -> tuple[bool, date]:
    if track.release_date is not None:
        return False, track.release_date
    if track.release_year is not None:
        return False, date(track.release_year, 1, 1)
    return True, date.max


def sort_tracks(tracks: Sequence[Track]) -> list[Track]:
    indexed_tracks = list(enumerate(tracks))

    def key(item: tuple[int, Track]) -> tuple[object, ...]:
        input_index, track = item
        release_missing, release_date = _release_key(track)
        track_order = track.track_number if track.track_number is not None else input_index
        return (
            _sort_text(track.artist),
            release_missing,
            release_date,
            _sort_text(track.album),
            _sort_text(track.album_type),
            track.track_number is None,
            track_order,
            input_index,
        )

    return [track for _, track in sorted(indexed_tracks, key=key)]


def dedupe_tracks(tracks: Iterable[Track]) -> list[Track]:
    seen_video_ids: set[str] = set()
    result: list[Track] = []
    for track in tracks:
        if track.video_id in seen_video_ids:
            continue
        seen_video_ids.add(track.video_id)
        result.append(track)
    return result


def prepare_tracks(tracks: Iterable[Track]) -> list[list[Track]]:
    """Order and deduplicate the complete catalog without content filtering."""
    ordered = sort_tracks(tracks)
    unique = dedupe_tracks(ordered)
    return [unique] if unique else []
