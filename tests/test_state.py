from pathlib import Path

import pytest

from playlist_builder.state import BuildState, StateError, load_state, save_state


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


def test_invalid_state_raises_state_error(tmp_path: Path) -> None:
    state_file = tmp_path / "state.json"
    state_file.write_text("[]", encoding="utf-8")

    with pytest.raises(StateError):
        load_state(state_file)
