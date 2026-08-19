from pathlib import Path

from playlist_builder.artists import artist_file_paths, read_artist_file, read_artist_lists, write_artist_file


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


def test_artist_file_paths_preserve_category_keys(tmp_path: Path) -> None:
    (tmp_path / "hip_hop_rap.txt").write_text("Run-DMC\n", encoding="utf-8")

    assert artist_file_paths(tmp_path) == {
        "hip_hop_rap": tmp_path / "hip_hop_rap.txt",
    }


def test_write_artist_file_deduplicates_and_sorts_names(tmp_path: Path) -> None:
    artist_file = tmp_path / "rock.txt"

    write_artist_file(artist_file, ["Radiohead", "deftones", " radiohead ", "Deftones"])

    assert artist_file.read_text(encoding="utf-8") == "deftones\nRadiohead\n"
