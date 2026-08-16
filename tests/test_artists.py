from pathlib import Path

from playlist_builder.artists import read_artist_file, read_artist_lists


def test_read_artist_file_ignores_comments_blanks_and_case_insensitive_duplicates(tmp_path: Path) -> None:
    artist_file = tmp_path / "rock.txt"
    artist_file.write_text(
        "# comment\n\nRadiohead\n radiohead \n\nDeftones\n",
        encoding="utf-8",
    )

    assert read_artist_file(artist_file) == ["Radiohead", "Deftones"]


def test_read_artist_lists_uses_sorted_txt_files_as_genres(tmp_path: Path) -> None:
    (tmp_path / "rock.txt").write_text("Radiohead\n", encoding="utf-8")
    (tmp_path / "metal.txt").write_text("Gojira\n", encoding="utf-8")
    (tmp_path / "notes.md").write_text("ignored\n", encoding="utf-8")

    assert read_artist_lists(tmp_path) == {
        "metal": ["Gojira"],
        "rock": ["Radiohead"],
    }
