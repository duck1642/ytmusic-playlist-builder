from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path


_INVALID_PLAYLIST_NAME_CHARACTERS = frozenset('<>:"/\\|?*')
_RESERVED_PLAYLIST_NAMES = {
    "con",
    "prn",
    "aux",
    "nul",
    *(f"com{index}" for index in range(1, 10)),
    *(f"lpt{index}" for index in range(1, 10)),
}


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


def validate_playlist_name(name: str) -> str:
    title = name.strip()
    if not title:
        raise ValueError("Playlist adı boş olamaz.")
    if title in {".", ".."}:
        raise ValueError("Playlist adı geçersiz.")
    if any(character in _INVALID_PLAYLIST_NAME_CHARACTERS for character in title):
        raise ValueError('Playlist adı şu karakterleri içeremez: < > : " / \\ | ? *')
    if any(ord(character) < 32 for character in title):
        raise ValueError("Playlist adı kontrol karakterleri içeremez.")
    if title.endswith((".", " ")):
        raise ValueError("Playlist adı nokta veya boşlukla bitemez.")
    reserved_name = title.split(".", 1)[0].casefold()
    if reserved_name in _RESERVED_PLAYLIST_NAMES:
        raise ValueError("Bu ad Windows için rezerve edilmiştir.")
    return title


def _find_playlist_file(directory: Path, name: str) -> Path:
    title = validate_playlist_name(name)
    if not directory.is_dir():
        raise FileNotFoundError(f"Artist directory does not exist: {directory}")
    for path in directory.glob("*.txt"):
        if path.stem.casefold() == title.casefold():
            return path
    raise FileNotFoundError(f"Playlist file does not exist: {title}.txt")


def create_playlist_file(directory: Path, name: str) -> Path:
    title = validate_playlist_name(name)
    directory.mkdir(parents=True, exist_ok=True)
    for path in directory.glob("*.txt"):
        if path.stem.casefold() == title.casefold():
            raise FileExistsError(f"Playlist file already exists: {path.name}")
    path = directory / f"{title}.txt"
    path.write_text("", encoding="utf-8")
    return path


def rename_playlist_file(directory: Path, old_name: str, new_name: str) -> Path:
    source = _find_playlist_file(directory, old_name)
    title = validate_playlist_name(new_name)
    if source.stem.casefold() == title.casefold():
        return source
    for path in directory.glob("*.txt"):
        if path.stem.casefold() == title.casefold():
            raise FileExistsError(f"Playlist file already exists: {path.name}")
    destination = directory / f"{title}.txt"
    source.rename(destination)
    return destination


def delete_playlist_file(directory: Path, name: str) -> Path:
    path = _find_playlist_file(directory, name)
    path.unlink()
    return path


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
