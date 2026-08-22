from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


class StateError(ValueError):
    """Raised when a saved build state cannot be read safely."""


STATE_VERSION = 1


@dataclass(frozen=True, slots=True)
class ArtistAlias:
    channel_id: str
    display_name: str
    resolved_at: str

    def to_dict(self) -> dict[str, str]:
        return {
            "channel_id": self.channel_id,
            "display_name": self.display_name,
            "resolved_at": self.resolved_at,
        }


@dataclass
class BuildState:
    artist_ids: dict[str, str] = field(default_factory=dict)
    artist_aliases: dict[str, ArtistAlias] = field(default_factory=dict)
    playlist_ids: dict[str, str] = field(default_factory=dict)
    generated_video_ids: dict[str, list[str]] = field(default_factory=dict)
    removed_video_ids: dict[str, list[str]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "state_version": STATE_VERSION,
            "artist_ids": self.artist_ids,
            "artist_aliases": {
                key: alias.to_dict() for key, alias in self.artist_aliases.items()
            },
            "playlist_ids": self.playlist_ids,
            "generated_video_ids": self.generated_video_ids,
            "removed_video_ids": self.removed_video_ids,
        }


def _string_mapping(raw: Any, field_name: str) -> dict[str, str]:
    if raw is None:
        return {}
    if not isinstance(raw, dict) or not all(
        isinstance(key, str) and isinstance(value, str) for key, value in raw.items()
    ):
        raise StateError(f"{field_name} must be a string-to-string mapping")
    return dict(raw)


def _string_list_mapping(raw: Any, field_name: str) -> dict[str, list[str]]:
    if raw is None:
        return {}
    if not isinstance(raw, dict) or not all(
        isinstance(key, str)
        and isinstance(value, list)
        and all(isinstance(item, str) for item in value)
        for key, value in raw.items()
    ):
        raise StateError(f"{field_name} must be a string-to-list-of-strings mapping")
    return {key: list(value) for key, value in raw.items()}


def _artist_alias_mapping(raw: Any) -> dict[str, ArtistAlias]:
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise StateError("artist_aliases must be a string-to-object mapping")

    aliases: dict[str, ArtistAlias] = {}
    for key, value in raw.items():
        if not isinstance(key, str) or not isinstance(value, dict):
            raise StateError("artist_aliases must be a string-to-object mapping")
        channel_id = value.get("channel_id")
        display_name = value.get("display_name")
        resolved_at = value.get("resolved_at")
        if not all(isinstance(item, str) and item for item in (channel_id, display_name, resolved_at)):
            raise StateError(
                "artist_aliases values must contain channel_id, display_name and resolved_at"
            )
        aliases[key] = ArtistAlias(channel_id, display_name, resolved_at)
    return aliases


def artist_alias_is_fresh(
    alias: ArtistAlias,
    max_age_days: int,
    *,
    now: datetime | None = None,
) -> bool:
    if max_age_days <= 0:
        return False
    try:
        resolved_at = datetime.fromisoformat(alias.resolved_at)
    except ValueError:
        return False
    if resolved_at.tzinfo is None:
        resolved_at = resolved_at.replace(tzinfo=timezone.utc)
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    return current - resolved_at <= timedelta(days=max_age_days)


def load_state(path: Path) -> BuildState:
    if not path.exists():
        return BuildState()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise StateError(f"Could not read state file: {path}") from error
    if not isinstance(raw, dict):
        raise StateError("State file must contain a JSON object")
    state_version = raw.get("state_version", STATE_VERSION)
    if state_version != STATE_VERSION:
        raise StateError(f"Unsupported state version: {state_version}")
    return BuildState(
        artist_ids=_string_mapping(raw.get("artist_ids"), "artist_ids"),
        artist_aliases=_artist_alias_mapping(raw.get("artist_aliases")),
        playlist_ids=_string_mapping(raw.get("playlist_ids"), "playlist_ids"),
        generated_video_ids=_string_list_mapping(
            raw.get("generated_video_ids"), "generated_video_ids"
        ),
        removed_video_ids=_string_list_mapping(raw.get("removed_video_ids"), "removed_video_ids"),
    )


def save_state(path: Path, state: BuildState) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(f"{path.suffix}.tmp")
    temporary_path.write_text(
        json.dumps(state.to_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary_path.replace(path)
