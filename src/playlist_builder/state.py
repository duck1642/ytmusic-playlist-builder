from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


class StateError(ValueError):
    """Raised when a saved build state cannot be read safely."""


@dataclass
class BuildState:
    artist_ids: dict[str, str] = field(default_factory=dict)
    playlist_ids: dict[str, str] = field(default_factory=dict)
    generated_video_ids: dict[str, list[str]] = field(default_factory=dict)
    removed_video_ids: dict[str, list[str]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "artist_ids": self.artist_ids,
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


def load_state(path: Path) -> BuildState:
    if not path.exists():
        return BuildState()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise StateError(f"Could not read state file: {path}") from error
    if not isinstance(raw, dict):
        raise StateError("State file must contain a JSON object")
    return BuildState(
        artist_ids=_string_mapping(raw.get("artist_ids"), "artist_ids"),
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
