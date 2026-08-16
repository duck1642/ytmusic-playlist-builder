from playlist_builder.models import Track
from playlist_builder.playlists import PlaylistWriter
from playlist_builder.state import BuildState


def track(video_id: str) -> Track:
    return Track(video_id=video_id, artist="Artist", album="Album", title=video_id)


class FakePlaylistApi:
    def __init__(self, playlists: list[dict[str, object]], tracks: dict[str, list[str]]) -> None:
        self.playlists = playlists
        self.tracks = tracks
        self.created: list[tuple[str, str, str, list[str]]] = []
        self.added: list[tuple[str, list[str]]] = []

    def list_playlists(self) -> list[dict[str, object]]:
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
    assert api.created == [("ROCK - RAW", "RAW playlist for ROCK", "PRIVATE", ["one", "two"])]
    assert state.playlist_ids == {"ROCK - RAW": "new-1"}
    assert state.generated_video_ids == {"ROCK - RAW": ["one", "two"]}


def test_append_only_does_not_restore_manually_removed_tracks() -> None:
    api = FakePlaylistApi(
        [{"playlistId": "PL-ROCK", "title": "ROCK - RAW"}],
        {"PL-ROCK": ["kept"]},
    )
    state = BuildState(
        playlist_ids={"ROCK - RAW": "PL-ROCK"},
        generated_video_ids={"ROCK - RAW": ["kept", "removed"]},
    )

    reports = PlaylistWriter(api).sync_genre(
        "rock", [[track("kept"), track("removed"), track("new")]], state
    )

    assert reports[0].added_video_ids == ("new",)
    assert reports[0].manually_removed_video_ids == ("removed",)
    assert api.added == [("PL-ROCK", ["new"])]
    assert state.removed_video_ids == {"ROCK - RAW": ["removed"]}
    assert state.generated_video_ids == {"ROCK - RAW": ["kept", "new"]}


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
