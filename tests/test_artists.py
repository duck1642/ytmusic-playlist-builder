from pathlib import Path

from playlist_builder.artists import (
    artist_file_paths,
    create_playlist_file,
    delete_playlist_file,
    read_artist_file,
    read_artist_entries,
    read_artist_lists,
    rename_playlist_file,
    validate_playlist_name,
    write_artist_file,
)


def test_read_artist_file_ignores_comments_blanks_and_case_insensitive_duplicates(tmp_path: Path) -> None:
    artist_file = tmp_path / "rock.txt"
    artist_file.write_text(
        "# comment\n\nRadiohead\n radiohead \n\nDeftones\n",
        encoding="utf-8",
    )

    assert read_artist_file(artist_file) == ["Radiohead", "Deftones"]


def test_read_artist_entries_preserves_duplicate_lines_and_locations(tmp_path: Path) -> None:
    artist_file = tmp_path / "rock.txt"
    artist_file.write_text("# comment\nRadiohead\n\nradiohead\n", encoding="utf-8")
    entries = read_artist_entries(artist_file)

    assert [(entry.line_number, entry.value) for entry in entries] == [
        (2, "Radiohead"),
        (4, "radiohead"),
    ]


def test_read_artist_lists_uses_sorted_txt_files_as_genres(tmp_path: Path) -> None:
    (tmp_path / "rock.txt").write_text("Radiohead\n", encoding="utf-8")
    (tmp_path / "metal.txt").write_text("Gojira\n", encoding="utf-8")
    (tmp_path / "notes.md").write_text("ignored\n", encoding="utf-8")

    assert read_artist_lists(tmp_path) == {
        "metal": ["Gojira"],
        "rock": ["Radiohead"],
    }


def test_artist_file_paths_preserve_category_keys(tmp_path: Path) -> None:
    (tmp_path / "hip_hop_rap.txt").write_text("Run-DMC\n", encoding="utf-8")

    assert artist_file_paths(tmp_path) == {
        "hip_hop_rap": tmp_path / "hip_hop_rap.txt",
    }


def test_write_artist_file_deduplicates_and_sorts_names(tmp_path: Path) -> None:
    artist_file = tmp_path / "rock.txt"

    write_artist_file(artist_file, ["Radiohead", "deftones", " radiohead ", "Deftones"])

    assert artist_file.read_text(encoding="utf-8") == "deftones\nRadiohead\n"


def test_playlist_file_lifecycle_uses_the_user_defined_name(tmp_path: Path) -> None:
    artists_dir = tmp_path / "artists"

    created = create_playlist_file(artists_dir, "METAL - RAW")
    created.write_text("Metallica\n", encoding="utf-8")
    assert created == artists_dir / "METAL - RAW.txt"
    assert read_artist_lists(artists_dir) == {"METAL - RAW": ["Metallica"]}

    renamed = rename_playlist_file(artists_dir, "METAL - RAW", "METAL")
    assert renamed == artists_dir / "METAL.txt"
    assert read_artist_file(renamed) == ["Metallica"]

    deleted = delete_playlist_file(artists_dir, "METAL")
    assert deleted == renamed
    assert not renamed.exists()


def test_playlist_name_rejects_path_like_names() -> None:
    for name in ("", "..", "a/b", "a\\b", "CON"):
        try:
            validate_playlist_name(name)
        except ValueError:
            continue
        raise AssertionError(f"Expected invalid playlist name: {name!r}")
