from __future__ import annotations

from pathlib import Path


def _artist_key(name: str) -> str:
    return name.casefold()


def read_artist_file(path: Path) -> list[str]:
    artists: list[str] = []
    seen: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        name = line.strip()
        if not name or name.startswith("#"):
            continue
        key = _artist_key(name)
        if key in seen:
            continue
        seen.add(key)
        artists.append(name)
    return artists


def read_artist_lists(directory: Path) -> dict[str, list[str]]:
    if not directory.is_dir():
        raise FileNotFoundError(f"Artist directory does not exist: {directory}")
    return {
        path.stem: read_artist_file(path)
        for path in sorted(directory.glob("*.txt"), key=lambda item: item.name.casefold())
    }
