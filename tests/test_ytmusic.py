import pytest
import ytmusicapi

from playlist_builder.ytmusic import (
    ArtistReference,
    YtMusicAdapter,
    YtMusicError,
    canonical_artist_key,
    normalize_artist_name,
    parse_artist_input,
)


class FakeYtMusic:
    def __init__(self) -> None:
        self.calls: list[tuple[object, ...]] = []

    def search(self, query: str, *, filter: str, limit: int) -> list[dict[str, object]]:
        self.calls.append(("search", query, filter, limit))
        return [
            {"resultType": "artist", "browseId": "UC-GOJIRA", "artist": "Gojira"},
            {"resultType": "artist", "browseId": "UC-OTHER", "artist": "Gojira Tribute"},
        ]

    def get_artist(self, channel_id: str) -> dict[str, object]:
        self.calls.append(("get_artist", channel_id))
        return {
            "albums": {"browseId": "UC-GOJIRA", "params": "albums-params"},
            "singles": {"browseId": "UC-GOJIRA", "params": "singles-params"},
        }

    def get_artist_albums(
        self, channel_id: str, params: str, *, limit: int | None
    ) -> list[dict[str, object]]:
        self.calls.append(("get_artist_albums", channel_id, params, limit))
        return [
            {"browseId": f"{params}-release", "title": params},
        ]


def test_resolve_artist_uses_exact_artist_match() -> None:
    client = FakeYtMusic()
    adapter = YtMusicAdapter(client)

    result = adapter.resolve_artist("Gojira")

    assert result == ArtistReference(requested_name="Gojira", display_name="Gojira", channel_id="UC-GOJIRA")
    assert client.calls == [("search", "Gojira", "artists", 10)]


def test_parse_artist_input_accepts_name_url_and_url_only_forms() -> None:
    assert parse_artist_input("Radiohead").display_name == "Radiohead"

    named = parse_artist_input(
        "Radiohead | https://music.youtube.com/@radiohead?si=example"
    )
    assert named.display_name == "Radiohead"
    assert named.handle == "radiohead"
    assert named.url == "https://music.youtube.com/@radiohead?si=example"

    channel = parse_artist_input(
        "https://music.youtube.com/channel/UC-RADIOHEAD?si=example"
    )
    assert channel.display_name is None
    assert channel.channel_id == "UC-RADIOHEAD"


def test_canonical_artist_keys_ignore_query_variants_but_keep_name_conservative() -> None:
    assert canonical_artist_key(" Radiohead ") == "name:radiohead"
    assert canonical_artist_key("https://music.youtube.com/@Radiohead?si=one") == "handle:radiohead"
    assert canonical_artist_key("https://music.youtube.com/@radiohead?si=two") == "handle:radiohead"
    assert normalize_artist_name("  Café  del  Mar ") == "café del mar"


def test_resolve_artist_uses_channel_url_without_search() -> None:
    client = FakeYtMusic()
    adapter = YtMusicAdapter(client)

    result = adapter.resolve_artist(
        "Radiohead | https://music.youtube.com/channel/UC-RADIOHEAD"
    )

    assert result == ArtistReference(
        requested_name="Radiohead | https://music.youtube.com/channel/UC-RADIOHEAD",
        display_name="Radiohead",
        channel_id="UC-RADIOHEAD",
    )
    assert client.calls == []


def test_resolve_artist_uses_handle_as_search_fallback() -> None:
    class HandleClient(FakeYtMusic):
        def search(self, query: str, *, filter: str, limit: int) -> list[dict[str, object]]:
            self.calls.append(("search", query, filter, limit))
            return [{"resultType": "artist", "browseId": "UC-RADIOHEAD", "artist": "Radiohead"}]

    client = HandleClient()
    result = YtMusicAdapter(client).resolve_artist(
        "https://music.youtube.com/@radiohead"
    )

    assert result == ArtistReference(
        requested_name="https://music.youtube.com/@radiohead",
        display_name="Radiohead",
        channel_id="UC-RADIOHEAD",
    )
    assert client.calls == [("search", "radiohead", "artists", 10)]


def test_resolve_artist_accepts_handle_when_display_name_differs() -> None:
    class OfficialHandleClient(FakeYtMusic):
        def search(self, query: str, *, filter: str, limit: int) -> list[dict[str, object]]:
            self.calls.append(("search", query, filter, limit))
            return [
                {
                    "resultType": "artist",
                    "browseId": "UC-RADIOHEAD",
                    "artist": "Radiohead",
                }
            ]

    client = OfficialHandleClient()
    result = YtMusicAdapter(client).resolve_artist(
        "https://music.youtube.com/@radioheadofficial"
    )

    assert result == ArtistReference(
        requested_name="https://music.youtube.com/@radioheadofficial",
        display_name="Radiohead",
        channel_id="UC-RADIOHEAD",
    )


def test_resolve_artist_rejects_ambiguous_handle_search() -> None:
    class AmbiguousHandleClient(FakeYtMusic):
        def search(self, query: str, *, filter: str, limit: int) -> list[dict[str, object]]:
            return [
                {"resultType": "artist", "browseId": "UC-ONE", "artist": "One"},
                {"resultType": "artist", "browseId": "UC-TWO", "artist": "Two"},
            ]

    with pytest.raises(YtMusicError, match="No exact artist match"):
        YtMusicAdapter(AmbiguousHandleClient()).resolve_artist(
            "https://music.youtube.com/@radioheadofficial"
        )


def test_resolve_artist_prefers_explicit_result_handle() -> None:
    class ExplicitHandleClient(FakeYtMusic):
        def search(self, query: str, *, filter: str, limit: int) -> list[dict[str, object]]:
            return [
                {
                    "resultType": "artist",
                    "browseId": "UC-OTHER",
                    "artist": "Other",
                    "handle": "other",
                },
                {
                    "resultType": "artist",
                    "browseId": "UC-RADIOHEAD",
                    "artist": "Radiohead",
                    "handle": "radioheadofficial",
                },
            ]

    result = YtMusicAdapter(ExplicitHandleClient()).resolve_artist(
        "https://music.youtube.com/@radioheadofficial"
    )

    assert result.channel_id == "UC-RADIOHEAD"


def test_resolve_artist_rejects_nonmatching_explicit_result_handle() -> None:
    class WrongExplicitHandleClient(FakeYtMusic):
        def search(self, query: str, *, filter: str, limit: int) -> list[dict[str, object]]:
            return [
                {
                    "resultType": "artist",
                    "browseId": "UC-OTHER",
                    "artist": "Other",
                    "handle": "other",
                }
            ]

    with pytest.raises(YtMusicError, match="No exact artist match"):
        YtMusicAdapter(WrongExplicitHandleClient()).resolve_artist(
            "https://music.youtube.com/@radioheadofficial"
        )


def test_resolve_artist_prefers_handle_when_name_and_url_are_both_given() -> None:
    class NamedHandleClient(FakeYtMusic):
        def search(self, query: str, *, filter: str, limit: int) -> list[dict[str, object]]:
            self.calls.append(("search", query, filter, limit))
            return [{"resultType": "artist", "browseId": "UC-RADIOHEAD", "artist": "Radiohead"}]

    client = NamedHandleClient()
    result = YtMusicAdapter(client).resolve_artist(
        "The Correct Label | https://music.youtube.com/@radiohead"
    )

    assert result.display_name == "The Correct Label"
    assert client.calls == [("search", "radiohead", "artists", 10)]


def test_resolve_artist_reuses_in_memory_aliases() -> None:
    client = FakeYtMusic()
    adapter = YtMusicAdapter(client)

    first = adapter.resolve_artist("Gojira")
    second = adapter.resolve_artist("gojira")

    assert first == second
    assert client.calls == [("search", "Gojira", "artists", 10)]


def test_parse_artist_input_rejects_unsupported_url_shape() -> None:
    with pytest.raises(YtMusicError, match="must use /@handle"):
        parse_artist_input("https://music.youtube.com/watch?v=video")


def test_resolve_artist_rejects_missing_exact_match() -> None:
    class NoMatch(FakeYtMusic):
        def search(self, query: str, *, filter: str, limit: int) -> list[dict[str, object]]:
            return [{"resultType": "artist", "browseId": "UC-OTHER", "artist": "Other"}]

    with pytest.raises(YtMusicError, match="No exact artist match"):
        YtMusicAdapter(NoMatch()).resolve_artist("Gojira")


def test_list_releases_fetches_full_album_and_single_sections() -> None:
    client = FakeYtMusic()
    adapter = YtMusicAdapter(client)
    reference = ArtistReference("Gojira", "Gojira", "UC-GOJIRA")

    releases = adapter.list_releases(reference)

    assert [release["browseId"] for release in releases] == [
        "albums-params-release",
        "singles-params-release",
    ]
    assert client.calls == [
        ("get_artist", "UC-GOJIRA"),
        ("get_artist_albums", "UC-GOJIRA", "albums-params", None),
        ("get_artist_albums", "UC-GOJIRA", "singles-params", None),
    ]


def test_verify_artist_checks_the_artist_page() -> None:
    client = FakeYtMusic()
    adapter = YtMusicAdapter(client)

    adapter.verify_artist(ArtistReference("Gojira", "Gojira", "UC-GOJIRA"))

    assert client.calls == [("get_artist", "UC-GOJIRA")]


def test_from_auth_passes_oauth_credentials(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    auth_file = tmp_path / "oauth.json"
    client_file = tmp_path / "client_secret.json"
    auth_file.write_text("{}", encoding="utf-8")
    client_file.write_text(
        '{"installed": {"client_id": "client-id", "client_secret": "client-secret"}}',
        encoding="utf-8",
    )
    calls: list[tuple[object, ...]] = []

    class FakeYTMusic:
        def __init__(self, *args: object, **kwargs: object) -> None:
            calls.append((args, kwargs))

    monkeypatch.setattr(ytmusicapi, "YTMusic", FakeYTMusic)

    YtMusicAdapter.from_auth(auth_file, oauth_client_file=client_file)

    assert calls[0][0] == (str(auth_file),)
    credentials = calls[0][1]["oauth_credentials"]
    assert credentials.client_id == "client-id"
    assert credentials.client_secret == "client-secret"
    assert calls[0][1]["requests_session"] is credentials._session


class PlaylistUpdateClient:
    def __init__(self, response: object) -> None:
        self.response = response
        self.calls: list[tuple[object, ...]] = []

    def add_playlist_items(
        self, playlist_id: str, *, videoIds: list[str], duplicates: bool
    ) -> object:
        self.calls.append((playlist_id, videoIds, duplicates))
        return self.response


def test_add_playlist_items_accepts_success_response() -> None:
    response = {"status": "STATUS_SUCCEEDED", "playlistEditResults": []}
    client = PlaylistUpdateClient(response)

    result = YtMusicAdapter(client).add_playlist_items("PL-ROCK", ["video-1"])

    assert result == response
    assert client.calls == [("PL-ROCK", ["video-1"], False)]


@pytest.mark.parametrize(
    "response",
    [
        {"status": "STATUS_FAILED"},
        {"error": "permission denied"},
        "STATUS_FAILED",
        None,
    ],
)
def test_add_playlist_items_rejects_non_success_response(response: object) -> None:
    with pytest.raises(YtMusicError, match="Could not add items"):
        YtMusicAdapter(PlaylistUpdateClient(response)).add_playlist_items(
            "PL-ROCK", ["video-1"]
        )
