from __future__ import annotations

from collections.abc import Iterable
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


def artist_file_paths(directory: Path) -> dict[str, Path]:
    if not directory.is_dir():
        raise FileNotFoundError(f"Artist directory does not exist: {directory}")
    return {
        path.stem: path
        for path in sorted(directory.glob("*.txt"), key=lambda item: item.name.casefold())
    }


def read_artist_lists(directory: Path) -> dict[str, list[str]]:
    return {
        genre: read_artist_file(path)
        for genre, path in artist_file_paths(directory).items()
    }


def write_artist_file(path: Path, artists: Iterable[str]) -> None:
    cleaned: list[str] = []
    seen: set[str] = set()
    for value in artists:
        name = value.strip()
        if not name or name.startswith("#"):
            continue
        key = _artist_key(name)
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(name)

    cleaned.sort(key=_artist_key)
    content = "\n".join(cleaned)
    if content:
        content += "\n"
    path.write_text(content, encoding="utf-8")
