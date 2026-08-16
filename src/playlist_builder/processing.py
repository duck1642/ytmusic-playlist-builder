from __future__ import annotations

import re
import unicodedata
from datetime import date
from typing import Iterable, Sequence

from .models import FilterConfig, Track


_FILTER_TERMS = {
    "exclude_live": ("live",),
    "exclude_remix": ("remix",),
    "exclude_remaster": ("remaster",),
    "exclude_deluxe": ("deluxe",),
    "exclude_karaoke": ("karaoke",),
}


def _sort_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.casefold())
    return "".join(character for character in normalized if not unicodedata.combining(character))


def _contains_term(text: str, term: str) -> bool:
    return re.search(rf"\b{re.escape(term)}\b", text) is not None or term in text


def filter_tracks(tracks: Iterable[Track], config: FilterConfig) -> list[Track]:
    enabled_terms = tuple(
        term
        for option, terms in _FILTER_TERMS.items()
        if getattr(config, option)
        for term in terms
    )
    if not enabled_terms:
        return list(tracks)

    result: list[Track] = []
    for track in tracks:
        searchable_text = f"{track.title} {track.album}".casefold()
        if not any(_contains_term(searchable_text, term) for term in enabled_terms):
            result.append(track)
    return result


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


def chunk_tracks(tracks: Sequence[Track], max_tracks: int) -> list[list[Track]]:
    if max_tracks <= 0:
        raise ValueError("max_tracks must be positive")
    return [list(tracks[index : index + max_tracks]) for index in range(0, len(tracks), max_tracks)]


def prepare_tracks(
    tracks: Iterable[Track],
    filter_config: FilterConfig,
    max_tracks: int,
) -> list[list[Track]]:
    filtered = filter_tracks(tracks, filter_config)
    ordered = sort_tracks(filtered)
    unique = dedupe_tracks(ordered)
    return chunk_tracks(unique, max_tracks)
