import pytest

from playlist_builder.models import Track
from playlist_builder.playlists import PlaylistIdentityError, PlaylistWriter
from playlist_builder.state import BuildState


def track(video_id: str) -> Track:
    return Track(video_id=video_id, artist="Artist", album="Album", title=video_id)


class FakePlaylistApi:
    def __init__(self, playlists: list[dict[str, object]], tracks: dict[str, list[str]]) -> None:
        self.playlists = playlists
        self.tracks = tracks
        self.created: list[tuple[str, str, str, list[str]]] = []
        self.added: list[tuple[str, list[str]]] = []
        self.playlist_lookups: list[str] = []

    def list_playlists(self) -> list[dict[str, object]]:
        self.playlist_lookups.append("list")
        return list(self.playlists)

    def get_playlist_video_ids(self, playlist_id: str) -> list[str]:
        return list(self.tracks[playlist_id])

    def create_playlist(
        self, title: str, description: str, privacy: str, video_ids: list[str]
    ) -> str:
        playlist_id = f"new-{len(self.created) + 1}"
        self.created.append((title, description, privacy, list(video_ids)))
        self.playlists.append({"playlistId": playlist_id, "title": title})
        self.tracks[playlist_id] = list(video_ids)
        return playlist_id

    def add_playlist_items(self, playlist_id: str, video_ids: list[str]) -> object:
        self.added.append((playlist_id, list(video_ids)))
        self.tracks[playlist_id].extend(video_ids)
        return "STATUS_SUCCEEDED"


def test_new_playlist_is_created_with_ordered_video_ids() -> None:
    api = FakePlaylistApi([], {})
    state = BuildState()

    reports = PlaylistWriter(api).sync_genre("rock", [[track("one"), track("two")]], state)

    assert reports[0].created is True
    assert reports[0].added_video_ids == ("one", "two")
    assert api.created == [("rock", "RAW playlist for rock", "PRIVATE", ["one", "two"])]
    assert state.playlist_ids == {"rock": "new-1"}
    assert state.generated_video_ids == {"rock": ["one", "two"]}


def test_append_only_does_not_restore_manually_removed_tracks() -> None:
    api = FakePlaylistApi(
        [{"playlistId": "PL-ROCK", "title": "rock"}],
        {"PL-ROCK": ["kept"]},
    )
    state = BuildState(
        playlist_ids={"rock": "PL-ROCK"},
        generated_video_ids={"rock": ["kept", "removed"]},
    )

    reports = PlaylistWriter(api).sync_genre(
        "rock", [[track("kept"), track("removed"), track("new")]], state
    )

    assert reports[0].added_video_ids == ("new",)
    assert reports[0].manually_removed_video_ids == ("removed",)
    assert api.added == [("PL-ROCK", ["new"])]
    assert state.removed_video_ids == {"rock": ["removed"]}
    assert state.generated_video_ids == {"rock": ["kept", "new"]}


def test_dry_run_does_not_write_playlist_or_state() -> None:
    api = FakePlaylistApi([], {})
    state = BuildState()

    reports = PlaylistWriter(api).sync_genre(
        "rock", [[track("one")]], state, dry_run=True
    )

    assert reports[0].created is True
    assert reports[0].added_video_ids == ("one",)
    assert api.created == []
    assert api.added == []
    assert state.to_dict() == BuildState().to_dict()


class FailingAddPlaylistApi(FakePlaylistApi):
    def add_playlist_items(self, playlist_id: str, video_ids: list[str]) -> object:
        self.added.append((playlist_id, list(video_ids)))
        raise RuntimeError("playlist update failed")


def test_failed_playlist_update_does_not_poison_state() -> None:
    api = FailingAddPlaylistApi(
        [{"playlistId": "PL-ROCK", "title": "rock"}],
        {"PL-ROCK": ["kept"]},
    )
    state = BuildState(
        playlist_ids={"rock": "PL-ROCK"},
        generated_video_ids={"rock": ["kept"]},
    )
    before = state.to_dict()

    with pytest.raises(RuntimeError, match="playlist update failed"):
        PlaylistWriter(api).sync_genre("rock", [[track("kept"), track("new")]], state)

    assert state.to_dict() == before


def test_deleted_playlist_id_is_recovered_from_current_title_lookup() -> None:
    api = FakePlaylistApi([], {})
    state = BuildState(
        playlist_ids={"rock": "deleted-id"},
        generated_video_ids={"rock": ["old"]},
    )

    reports = PlaylistWriter(api).sync_genre("rock", [[track("new")]], state)

    assert reports[0].created is True
    assert api.playlist_lookups == ["list"]
    assert api.created == [("rock", "RAW playlist for rock", "PRIVATE", ["new"])]
    assert state.playlist_ids == {"rock": "new-1"}
    assert state.removed_video_ids == {"rock": []}
    assert state.generated_video_ids == {"rock": ["new"]}


def test_recreated_playlist_does_not_mark_previous_tracks_as_removed() -> None:
    api = FakePlaylistApi([], {})
    state = BuildState(
        playlist_ids={"rock": "deleted-id"},
        generated_video_ids={"rock": ["old"]},
    )

    report = PlaylistWriter(api).sync_playlist(
        "rock", [track("new")], state, privacy="PRIVATE"
    )

    assert report.manually_removed_video_ids == ()
    assert state.removed_video_ids == {"rock": []}
    assert state.generated_video_ids == {"rock": ["new"]}


def test_saved_playlist_id_is_preferred_over_duplicate_title_match() -> None:
    api = FakePlaylistApi(
        [
            {"playlistId": "PL-WRONG", "title": "rock"},
            {"playlistId": "PL-MANAGED", "title": "rock"},
        ],
        {"PL-WRONG": ["wrong"], "PL-MANAGED": ["kept"]},
    )
    state = BuildState(
        playlist_ids={"rock": "PL-MANAGED"},
        generated_video_ids={"rock": ["kept"]},
    )

    PlaylistWriter(api).sync_playlist(
        "rock", [track("kept"), track("new")], state, privacy="PRIVATE"
    )

    assert api.added == [("PL-MANAGED", ["new"])]
    assert state.playlist_ids == {"rock": "PL-MANAGED"}


def test_saved_playlist_id_is_ignored_when_remote_title_changed() -> None:
    api = FakePlaylistApi(
        [
            {"playlistId": "PL-SAVED", "title": "renamed rock"},
            {"playlistId": "PL-ROCK", "title": "rock"},
        ],
        {"PL-SAVED": ["wrong"], "PL-ROCK": ["kept"]},
    )
    state = BuildState(
        playlist_ids={"rock": "PL-SAVED"},
        generated_video_ids={"rock": ["kept"]},
    )

    PlaylistWriter(api).sync_playlist(
        "rock", [track("kept"), track("new")], state, privacy="PRIVATE"
    )

    assert api.added == [("PL-ROCK", ["new"])]
    assert state.playlist_ids == {"rock": "PL-ROCK"}


def test_ambiguous_playlist_title_is_rejected_without_valid_saved_id() -> None:
    api = FakePlaylistApi(
        [
            {"playlistId": "PL-ONE", "title": "rock"},
            {"playlistId": "PL-TWO", "title": "rock"},
        ],
        {"PL-ONE": [], "PL-TWO": []},
    )

    with pytest.raises(PlaylistIdentityError, match="Multiple playlists found"):
        PlaylistWriter(api).sync_playlist("rock", [track("new")], BuildState(), privacy="PRIVATE")


class FailingPlaylistLookupApi(FakePlaylistApi):
    def list_playlists(self) -> list[dict[str, object]]:
        raise RuntimeError("playlist lookup failed")


def test_playlist_lookup_failure_does_not_create_or_mutate_state() -> None:
    api = FailingPlaylistLookupApi([], {})
    state = BuildState(
        playlist_ids={"rock": "possibly-valid-id"},
        generated_video_ids={"rock": ["old"]},
    )
    before = state.to_dict()

    with pytest.raises(RuntimeError, match="playlist lookup failed"):
        PlaylistWriter(api).sync_genre("rock", [[track("new")]], state)

    assert api.created == []
    assert state.to_dict() == before
