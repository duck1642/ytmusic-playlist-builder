from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .models import FilterConfig


class ConfigError(ValueError):
    """Raised when the project configuration is invalid."""


@dataclass(frozen=True, slots=True)
class PlaylistConfig:
    privacy: str = "PRIVATE"
    update_mode: str = "append_only"


@dataclass(frozen=True, slots=True)
class AppConfig:
    auth_file: Path | None
    oauth_client_file: Path | None
    artists_dir: Path
    state_dir: Path
    cache_dir: Path
    logs_dir: Path
    artist_cache_ttl_days: int
    playlist: PlaylistConfig
    filters: FilterConfig


def _relative_path(base_dir: Path, value: Any, field_name: str) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"{field_name} must be a non-empty path")
    path = Path(value)
    return path if path.is_absolute() else base_dir / path


def _optional_path(base_dir: Path, value: Any, field_name: str) -> Path | None:
    if value is None:
        return None
    return _relative_path(base_dir, value, field_name)


def _bool_value(value: Any, field_name: str) -> bool:
    if isinstance(value, bool):
        return value
    raise ConfigError(f"{field_name} must be true or false")


def load_config(path: Path) -> AppConfig:
    base_dir = path.parent
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as error:
        raise ConfigError(f"Invalid YAML in {path}: {error}") from error

    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        raise ConfigError("The top-level configuration must be a mapping")

    playlist_data = raw.get("playlist", {})
    filters_data = raw.get("filters", {})
    if not isinstance(playlist_data, dict) or not isinstance(filters_data, dict):
        raise ConfigError("playlist and filters must be mappings")

    privacy = str(playlist_data.get("privacy", "PRIVATE")).upper()
    if privacy not in {"PRIVATE", "PUBLIC", "UNLISTED"}:
        raise ConfigError("playlist.privacy must be PRIVATE, PUBLIC or UNLISTED")

    update_mode = str(playlist_data.get("update_mode", "append_only")).casefold()
    if update_mode != "append_only":
        raise ConfigError("Only append_only update_mode is supported")

    raw_artist_cache_ttl = raw.get("artist_cache_ttl_days", 30)
    if isinstance(raw_artist_cache_ttl, bool):
        raise ConfigError("artist_cache_ttl_days must be a non-negative integer")
    try:
        artist_cache_ttl_days = int(raw_artist_cache_ttl)
    except (TypeError, ValueError) as error:
        raise ConfigError("artist_cache_ttl_days must be a non-negative integer") from error
    if artist_cache_ttl_days < 0:
        raise ConfigError("artist_cache_ttl_days must be a non-negative integer")

    filter_config = FilterConfig(
        exclude_live=_bool_value(filters_data.get("exclude_live", False), "filters.exclude_live"),
        exclude_remix=_bool_value(filters_data.get("exclude_remix", False), "filters.exclude_remix"),
        exclude_remaster=_bool_value(
            filters_data.get("exclude_remaster", False), "filters.exclude_remaster"
        ),
        exclude_deluxe=_bool_value(
            filters_data.get("exclude_deluxe", False), "filters.exclude_deluxe"
        ),
        exclude_karaoke=_bool_value(
            filters_data.get("exclude_karaoke", False), "filters.exclude_karaoke"
        ),
    )
    return AppConfig(
        auth_file=_optional_path(base_dir, raw.get("auth_file"), "auth_file"),
        oauth_client_file=_optional_path(
            base_dir,
            raw.get("oauth_client_file", "auth/client_secret.json"),
            "oauth_client_file",
        ),
        artists_dir=_relative_path(base_dir, raw.get("artists_dir", "artists"), "artists_dir"),
        state_dir=_relative_path(base_dir, raw.get("state_dir", "state"), "state_dir"),
        cache_dir=_relative_path(base_dir, raw.get("cache_dir", "cache"), "cache_dir"),
        logs_dir=_relative_path(base_dir, raw.get("logs_dir", "logs"), "logs_dir"),
        artist_cache_ttl_days=artist_cache_ttl_days,
        playlist=PlaylistConfig(
            privacy=privacy,
            update_mode=update_mode,
        ),
        filters=filter_config,
    )
