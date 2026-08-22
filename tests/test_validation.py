from pathlib import Path

from playlist_builder.validation import format_validation_report, validate_artist_files


def test_validation_reports_duplicate_inputs_without_editing_files(tmp_path: Path) -> None:
    artists_dir = tmp_path / "artists"
    artists_dir.mkdir()
    artist_file = artists_dir / "rock.txt"
    original = (
        "Radiohead\n"
        "radiohead\n"
        "https://music.youtube.com/@Radiohead?si=one\n"
        "https://music.youtube.com/@radiohead?si=two\n"
    )
    artist_file.write_text(original, encoding="utf-8")

    report = validate_artist_files(artists_dir)

    assert not report.is_valid
    assert [(issue.kind, issue.line_number, issue.duplicate_of_line) for issue in report.issues] == [
        ("duplicate", 2, 1),
        ("duplicate", 4, 3),
    ]
    assert artist_file.read_text(encoding="utf-8") == original
    assert any("rock.txt:2" in line for line in format_validation_report(report))


def test_validation_reports_invalid_youtube_url(tmp_path: Path) -> None:
    artists_dir = tmp_path / "artists"
    artists_dir.mkdir()
    (artists_dir / "rock.txt").write_text(
        "Radiohead | https://music.youtube.com/watch?v=video\n",
        encoding="utf-8",
    )

    report = validate_artist_files(artists_dir)

    assert len(report.issues) == 1
    assert report.issues[0].kind == "invalid"
    assert report.issues[0].line_number == 1
