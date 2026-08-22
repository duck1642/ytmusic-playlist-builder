from datetime import date

from playlist_builder.models import Track
from playlist_builder.processing import (
    dedupe_tracks,
    prepare_tracks,
    sort_tracks,
)


def track(
    video_id: str,
    artist: str,
    album: str,
    title: str,
    *,
    release_year: int | None = None,
    track_number: int | None = None,
    release_date: date | None = None,
) -> Track:
    return Track(
        video_id=video_id,
        artist=artist,
        album=album,
        title=title,
        release_year=release_year,
        release_date=release_date,
        track_number=track_number,
    )


def test_sort_groups_artists_then_albums_then_original_track_order() -> None:
    tracks = [
        track("b", "Beta", "First", "Beta song", release_year=2020, track_number=1),
        track("a2", "Alpha", "Later", "Alpha later", release_year=2020, track_number=1),
        track("a1-2", "Alpha", "Early", "Alpha second", release_year=2010, track_number=2),
        track("a1-1", "Alpha", "Early", "Alpha first", release_year=2010, track_number=1),
    ]

    assert [item.video_id for item in sort_tracks(tracks)] == [
        "a1-1",
        "a1-2",
        "a2",
        "b",
    ]


def test_sort_preserves_input_order_when_track_number_is_missing() -> None:
    tracks = [
        track("second", "Artist", "Album", "Second", release_year=2020),
        track("first", "Artist", "Album", "First", release_year=2020),
    ]

    assert [item.video_id for item in sort_tracks(tracks)] == ["second", "first"]


def test_dedupe_keeps_first_occurrence_by_video_id() -> None:
    tracks = [track("same", "Artist", "Album", "Song"), track("same", "Artist", "Single", "Song")]

    result = dedupe_tracks(tracks)

    assert len(result) == 1
    assert result[0].album == "Album"


def test_prepare_tracks_keeps_all_release_variants_and_dedupes_without_chunking() -> None:
    tracks = [
        track("karaoke", "Artist", "Album", "Song (Karaoke)", release_year=2024, track_number=1),
        track("remix", "Artist", "Album", "Song (Remix)", release_year=2020, track_number=1),
        track("duplicate", "Artist", "Album", "Song", release_year=2025, track_number=1),
        track("live", "Artist", "Album (Live)", "Song", release_year=2019, track_number=1),
        track("deluxe", "Artist", "Album (Deluxe)", "Song", release_year=2022, track_number=1),
        track("remaster", "Artist", "Album (Remaster)", "Song", release_year=2021, track_number=1),
        track("duplicate", "Artist", "Single", "Song", release_year=2026, track_number=1),
    ]

    result = prepare_tracks(tracks)

    assert [[item.video_id for item in chunk] for chunk in result] == [[
        "live",
        "remix",
        "remaster",
        "deluxe",
        "karaoke",
        "duplicate",
    ]]


def test_prepare_tracks_keeps_more_than_550_tracks_in_one_playlist() -> None:
    tracks = [
        track(str(index), "Artist", "Album", str(index), track_number=index)
        for index in range(551)
    ]

    result = prepare_tracks(tracks)

    assert len(result) == 1
    assert len(result[0]) == 551
