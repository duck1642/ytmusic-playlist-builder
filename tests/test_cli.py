from datetime import datetime, timezone
from pathlib import Path

import pytest

from playlist_builder.cli import (
    build_parser,
    main,
    run,
    validate_format,
    validate_remote,
)
from playlist_builder.playlists import PlaylistIdentityError
from playlist_builder.state import ArtistAlias, BuildState, load_state, save_state
from playlist_builder.ytmusic import ArtistInput, ArtistReference, parse_artist_input


class FakeBuildApi:
    def __init__(self) -> None:
        self.resolve_calls: list[str] = []
        self.list_releases_calls = 0

    def resolve_artist(self, value: str | ArtistInput) -> ArtistReference:
        self.resolve_calls.append(value.raw if isinstance(value, ArtistInput) else value)
        artist_input = value if isinstance(value, ArtistInput) else parse_artist_input(value)
        return ArtistReference(
            requested_name=artist_input.raw,
            display_name=artist_input.display_name or "Radiohead",
            channel_id="UC-RADIOHEAD",
        )

    def list_releases(self, _artist: ArtistReference) -> list[dict[str, object]]:
        self.list_releases_calls += 1
        return [{"browseId": "ALBUM-1", "title": "Album", "year": "2000"}]

    def get_album(self, _browse_id: str) -> dict[str, object]:
        return {
            "title": "Album",
            "year": "2000",
            "tracks": [{"videoId": "track-1", "title": "Track", "trackNumber": 0}],
        }


class FakeWriter:
    calls: list[tuple[str, list[str]]] = []

    def __init__(self, _api: object) -> None:
        pass

    def sync_genre(self, genre: str, chunks: list[list[object]], *_args, **_kwargs) -> list[object]:
        self.calls.append((genre, [track.video_id for chunk in chunks for track in chunk]))
        return []


def _write_config(tmp_path: Path) -> Path:
    artists_dir = tmp_path / "artists"
    artists_dir.mkdir()
    (artists_dir / "rock.txt").write_text(
        "Radiohead\nradiohead\nRadiohead | https://music.youtube.com/@radiohead\n",
        encoding="utf-8",
    )
    (artists_dir / "zzfocus.txt").write_text(
        "https://music.youtube.com/@radiohead?si=example\n",
        encoding="utf-8",
    )
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        "\n".join(
            (
                "auth_file: auth/oauth.json",
                "artists_dir: artists",
                "state_dir: state",
                "cache_dir: cache",
                "logs_dir: logs",
                "artist_cache_ttl_days: 30",
                "playlist:",
                "  privacy: PRIVATE",
            )
        ),
        encoding="utf-8",
    )
    return config_path


def test_validate_format_command_is_network_free_and_requires_approval_for_changes(
    tmp_path: Path,
) -> None:
    config_path = _write_config(tmp_path)
    output: list[str] = []

    assert validate_format(config_path, output_fn=output.append, input_fn=lambda _: "n") == 1
    assert any("rock.txt:2" in line for line in output)
    assert not (tmp_path / "state" / "build_state.json").exists()
    assert not (tmp_path / "cache").exists()


def test_parser_exposes_two_validation_modes_without_old_alias() -> None:
    format_args = build_parser().parse_args(["--validate-format"])
    remote_args = build_parser().parse_args(["--validate-remote"])

    assert format_args.validate_format is True
    assert remote_args.validate_remote is True
    with pytest.raises(SystemExit):
        build_parser().parse_args(["--validate"])


def test_main_reports_playlist_identity_error_without_traceback(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    def fail_run(*_args, **_kwargs) -> int:
        raise PlaylistIdentityError(
            "Multiple playlists found with title 'rock': PL-ONE, PL-TWO"
        )

    monkeypatch.setattr("playlist_builder.cli.run", fail_run)

    assert main(["--config", str(tmp_path / "config.yaml")]) == 2

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == (
        "Error: Multiple playlists found with title 'rock': PL-ONE, PL-TWO\n"
    )


class FakeRemoteApi:
    def resolve_artist(self, value: str | ArtistInput) -> ArtistReference:
        artist_input = value if isinstance(value, ArtistInput) else parse_artist_input(value)
        return ArtistReference(artist_input.raw, artist_input.label, "UC-RADIOHEAD")

    def verify_artist(self, _artist: ArtistReference) -> None:
        return None


def test_validate_remote_only_applies_changes_after_approval(tmp_path: Path, monkeypatch) -> None:
    config_path = _write_config(tmp_path)
    api = FakeRemoteApi()

    def fake_from_auth(cls, *_args, **_kwargs):
        return api

    monkeypatch.setattr(
        "playlist_builder.cli.YtMusicAdapter.from_auth",
        classmethod(fake_from_auth),
    )

    artist_file = tmp_path / "artists" / "rock.txt"
    original = artist_file.read_text(encoding="utf-8")
    assert validate_remote(config_path, input_fn=lambda _: "n") == 1
    assert artist_file.read_text(encoding="utf-8") == original

    assert validate_remote(config_path, input_fn=lambda _: "y") == 0
    assert artist_file.read_text(encoding="utf-8") == "Radiohead\n"
    assert not (tmp_path / "state" / "build_state.json").exists()
    assert not (tmp_path / "cache").exists()


def test_run_deduplicates_per_playlist_and_reuses_aliases_and_catalog(
    tmp_path: Path,
    monkeypatch,
) -> None:
    config_path = _write_config(tmp_path)
    api = FakeBuildApi()
    FakeWriter.calls = []

    def fake_from_auth(cls, *_args, **_kwargs):
        return api

    monkeypatch.setattr(
        "playlist_builder.cli.YtMusicAdapter.from_auth",
        classmethod(fake_from_auth),
    )
    monkeypatch.setattr("playlist_builder.cli.PlaylistWriter", FakeWriter)

    assert run(config_path) == 0

    assert api.resolve_calls == [
        "Radiohead",
        "Radiohead | https://music.youtube.com/@radiohead",
    ]
    assert api.list_releases_calls == 1
    assert FakeWriter.calls == [("rock", ["track-1"]), ("zzfocus", ["track-1"])]
    state = load_state(tmp_path / "state" / "build_state.json")
    assert "name:radiohead" in state.artist_aliases
    assert "handle:radiohead" in state.artist_aliases

    api.resolve_calls.clear()
    api.list_releases_calls = 0
    FakeWriter.calls = []

    assert run(config_path) == 0

    assert api.resolve_calls == []
    assert api.list_releases_calls == 1


def test_run_does_not_use_legacy_handle_alias_without_provenance(
    tmp_path: Path,
    monkeypatch,
) -> None:
    config_path = _write_config(tmp_path)
    save_state(
        tmp_path / "state" / "build_state.json",
        BuildState(
            artist_aliases={
                "handle:radiohead": ArtistAlias(
                    channel_id="UC-LEGACY",
                    display_name="Radiohead",
                    resolved_at=datetime.now(timezone.utc).isoformat(),
                )
            }
        ),
    )
    api = FakeBuildApi()
    FakeWriter.calls = []

    def fake_from_auth(cls, *_args, **_kwargs):
        return api

    monkeypatch.setattr(
        "playlist_builder.cli.YtMusicAdapter.from_auth",
        classmethod(fake_from_auth),
    )
    monkeypatch.setattr("playlist_builder.cli.PlaylistWriter", FakeWriter)

    assert run(config_path) == 0

    assert api.resolve_calls == [
        "Radiohead",
        "Radiohead | https://music.youtube.com/@radiohead",
    ]
    state = load_state(tmp_path / "state" / "build_state.json")
    assert state.artist_aliases["handle:radiohead"].channel_id == "UC-RADIOHEAD"
    assert state.artist_aliases["handle:radiohead"].handle_verified is True


def test_run_does_not_use_legacy_artist_ids_without_ttl_metadata(
    tmp_path: Path,
    monkeypatch,
) -> None:
    config_path = _write_config(tmp_path)
    save_state(
        tmp_path / "state" / "build_state.json",
        BuildState(artist_ids={"Radiohead": "UC-LEGACY"}),
    )
    api = FakeBuildApi()
    FakeWriter.calls = []

    def fake_from_auth(cls, *_args, **_kwargs):
        return api

    monkeypatch.setattr(
        "playlist_builder.cli.YtMusicAdapter.from_auth",
        classmethod(fake_from_auth),
    )
    monkeypatch.setattr("playlist_builder.cli.PlaylistWriter", FakeWriter)

    assert run(config_path) == 0

    assert "Radiohead" in api.resolve_calls
    assert load_state(tmp_path / "state" / "build_state.json").artist_ids == {
        "Radiohead": "UC-LEGACY"
    }
