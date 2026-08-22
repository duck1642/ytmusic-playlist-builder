from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
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


@dataclass(frozen=True, slots=True)
class ArtistEntry:
    """A non-empty artist-list line, retained with its source location."""

    path: Path
    line_number: int
    value: str


def _artist_key(name: str) -> str:
    return name.casefold()


def read_artist_entries(path: Path) -> list[ArtistEntry]:
    entries: list[ArtistEntry] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        value = line.strip()
        if not value or value.startswith("#"):
            continue
        entries.append(ArtistEntry(path, line_number, value))
    return entries


def read_artist_file(path: Path) -> list[str]:
    artists: list[str] = []
    seen: set[str] = set()
    for entry in read_artist_entries(path):
        name = entry.value
        key = _artist_key(name)
        if key in seen:
            continue
        seen.add(key)
        artists.append(name)
    return artists


def read_artist_file_lines(path: Path) -> list[str]:
    with path.open("r", encoding="utf-8", newline="") as source:
        return source.read().splitlines(keepends=True)


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


def read_artist_entry_lists(directory: Path) -> dict[str, list[ArtistEntry]]:
    return {
        genre: read_artist_entries(path)
        for genre, path in artist_file_paths(directory).items()
    }


def apply_artist_line_changes(path: Path, changes: Mapping[int, str | None]) -> None:
    """Apply approved line changes while preserving untouched text and line endings."""

    if not changes:
        return
    with path.open("r", encoding="utf-8", newline="") as source:
        lines = source.read().splitlines(keepends=True)

    unknown_lines = set(changes).difference(range(1, len(lines) + 1))
    if unknown_lines:
        raise ValueError(f"Artist file line does not exist: {path}:{min(unknown_lines)}")

    updated_lines: list[str] = []
    for line_number, line in enumerate(lines, start=1):
        replacement = changes.get(line_number, line)
        if replacement is None:
            continue
        if replacement == line:
            updated_lines.append(line)
            continue
        if line.endswith("\r\n"):
            line_ending = "\r\n"
        elif line.endswith(("\n", "\r")):
            line_ending = line[-1]
        else:
            line_ending = ""
        updated_lines.append(replacement + line_ending)

    temporary_path = path.with_name(f".{path.name}.tmp")
    try:
        with temporary_path.open("w", encoding="utf-8", newline="") as target:
            target.write("".join(updated_lines))
        temporary_path.replace(path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


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


def write_artist_file_preserving_layout(
    path: Path, source_lines: Sequence[str], artists: Iterable[str]
) -> None:
    """Write edited artists while preserving comments, blanks, order, and line endings."""

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

    lines = list(source_lines)
    line_ending = next(
        (
            "\r\n"
            if line.endswith("\r\n")
            else line[-1]
            for line in lines
            if line.endswith("\r\n") or line.endswith(("\n", "\r"))
        ),
        "\n",
    )
    artist_index = 0
    updated_lines: list[str] = []
    for line in lines:
        content = line.rstrip("\r\n")
        if not content.strip() or content.lstrip().startswith("#"):
            updated_lines.append(line)
            continue
        if artist_index >= len(cleaned):
            continue
        name = cleaned[artist_index]
        artist_index += 1
        if name == content.strip():
            updated_lines.append(line)
            continue
        if line.endswith("\r\n"):
            ending = "\r\n"
        elif line.endswith(("\n", "\r")):
            ending = line[-1]
        else:
            ending = ""
        updated_lines.append(name + ending)

    if artist_index < len(cleaned):
        if updated_lines and not updated_lines[-1].endswith(("\r", "\n")):
            updated_lines[-1] += line_ending
        updated_lines.extend(
            name + line_ending for name in cleaned[artist_index:]
        )

    temporary_path = path.with_name(f".{path.name}.tmp")
    try:
        with temporary_path.open("w", encoding="utf-8", newline="") as target:
            target.write("".join(updated_lines))
        temporary_path.replace(path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()
