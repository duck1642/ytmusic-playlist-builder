from pathlib import Path

import pytest

from playlist_builder.config import ConfigError, load_config


def test_load_config_resolves_relative_paths_from_config_directory(tmp_path: Path) -> None:
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        """
artists_dir: artists
auth_file: auth/oauth.json
playlist:
  privacy: PRIVATE
  max_tracks: 25
  update_mode: append_only
filters:
  exclude_karaoke: true
""",
        encoding="utf-8",
    )

    config = load_config(config_file)

    assert config.artists_dir == tmp_path / "artists"
    assert config.auth_file == tmp_path / "auth" / "oauth.json"
    assert config.oauth_client_file == tmp_path / "auth" / "client_secret.json"
    assert config.playlist.max_tracks == 25
    assert config.filters.exclude_karaoke is True
    assert config.artist_cache_ttl_days == 30


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("max_tracks", 0),
        ("max_tracks", -1),
        ("privacy", "INVALID"),
        ("update_mode", "reconcile"),
    ],
)
def test_load_config_rejects_unsupported_playlist_settings(
    tmp_path: Path,
    field: str,
    value: object,
) -> None:
    config_file = tmp_path / "config.yaml"
    if field == "max_tracks":
        contents = f"playlist:\n  max_tracks: {value}\n"
    else:
        contents = f"playlist:\n  {field}: {value}\n"
    config_file.write_text(contents, encoding="utf-8")

    with pytest.raises(ConfigError):
        load_config(config_file)


@pytest.mark.parametrize("value", [-1, "not-a-number", True])
def test_load_config_rejects_invalid_artist_cache_ttl(tmp_path: Path, value: object) -> None:
    config_file = tmp_path / "config.yaml"
    config_file.write_text(f"artist_cache_ttl_days: {value}\n", encoding="utf-8")

    with pytest.raises(ConfigError):
        load_config(config_file)
