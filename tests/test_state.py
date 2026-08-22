from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from playlist_builder.state import (
    ArtistAlias,
    BuildState,
    StateError,
    artist_alias_is_fresh,
    load_state,
    save_state,
)


def test_missing_state_loads_empty_state(tmp_path: Path) -> None:
    state = load_state(tmp_path / "state.json")

    assert state == BuildState()


def test_state_round_trip_creates_parent_directory(tmp_path: Path) -> None:
    state_file = tmp_path / "state" / "build.json"
    expected = BuildState(
        artist_ids={"Radiohead": "artist-id"},
        playlist_ids={"rock": "playlist-id"},
        generated_video_ids={"rock": ["song-1"]},
        removed_video_ids={"rock": ["song-2"]},
    )

    save_state(state_file, expected)

    assert load_state(state_file) == expected


def test_state_round_trip_preserves_artist_aliases(tmp_path: Path) -> None:
    state_file = tmp_path / "state.json"
    expected = BuildState(
        artist_aliases={
            "name:radiohead": ArtistAlias(
                channel_id="UC-RADIOHEAD",
                display_name="Radiohead",
                resolved_at="2026-08-22T00:00:00+00:00",
            )
        }
    )

    save_state(state_file, expected)

    assert load_state(state_file) == expected


def test_legacy_state_without_version_still_loads(tmp_path: Path) -> None:
    state_file = tmp_path / "state.json"
    state_file.write_text('{"artist_ids": {"Radiohead": "UC-RADIOHEAD"}}', encoding="utf-8")

    assert load_state(state_file).artist_ids == {"Radiohead": "UC-RADIOHEAD"}


def test_artist_alias_freshness_respects_ttl() -> None:
    now = datetime(2026, 8, 22, tzinfo=timezone.utc)
    alias = ArtistAlias(
        channel_id="UC-RADIOHEAD",
        display_name="Radiohead",
        resolved_at=(now - timedelta(days=2)).isoformat(),
    )

    assert artist_alias_is_fresh(alias, 2, now=now)
    assert not artist_alias_is_fresh(alias, 1, now=now)
    assert not artist_alias_is_fresh(alias, 0, now=now)


def test_invalid_state_raises_state_error(tmp_path: Path) -> None:
    state_file = tmp_path / "state.json"
    state_file.write_text("[]", encoding="utf-8")

    with pytest.raises(StateError):
        load_state(state_file)
