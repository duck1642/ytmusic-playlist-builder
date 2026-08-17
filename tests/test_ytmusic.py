import pytest
import ytmusicapi

from playlist_builder.ytmusic import ArtistReference, YtMusicAdapter, YtMusicError


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
