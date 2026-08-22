from pathlib import Path

from playlist_builder.validation import (
    apply_artist_changes,
    format_remote_validation_report,
    format_validation_report,
    validate_format_files,
    validate_remote_artist_files,
)
from playlist_builder.ytmusic import ArtistInput, ArtistReference, YtMusicError, parse_artist_input


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

    report = validate_format_files(artists_dir)

    assert not report.is_valid
    assert [(issue.kind, issue.line_number, issue.duplicate_of_line) for issue in report.issues] == [
        ("duplicate", 2, 1),
        ("duplicate", 4, 3),
    ]
    assert [change.line_number for change in report.changes] == [2, 4]
    assert artist_file.read_text(encoding="utf-8") == original
    assert any("rock.txt:2" in line for line in format_validation_report(report))


def test_validation_reports_invalid_youtube_url(tmp_path: Path) -> None:
    artists_dir = tmp_path / "artists"
    artists_dir.mkdir()
    (artists_dir / "rock.txt").write_text(
        "Radiohead | https://music.youtube.com/watch?v=video\n",
        encoding="utf-8",
    )

    report = validate_format_files(artists_dir)

    assert len(report.issues) == 1
    assert report.issues[0].kind == "invalid"
    assert report.issues[0].line_number == 1
    assert report.issues[0].suggestion is not None
    assert not report.changes


def test_apply_artist_changes_preserves_comments_order_and_line_endings(tmp_path: Path) -> None:
    artists_dir = tmp_path / "artists"
    artists_dir.mkdir()
    artist_file = artists_dir / "rock.txt"
    artist_file.write_bytes(b"# keep\r\nRadiohead\r\nradiohead\r\n\r\nDeftones\r\n")

    report = validate_format_files(artists_dir)
    apply_artist_changes(report.changes)

    assert artist_file.read_bytes() == b"# keep\r\nRadiohead\r\n\r\nDeftones\r\n"


class FakeRemoteApi:
    def resolve_artist(self, value: str | ArtistInput) -> ArtistReference:
        artist_input = value if isinstance(value, ArtistInput) else parse_artist_input(value)
        channel_id = "UC-DEFTONES" if artist_input.label.casefold() == "deftones" else "UC-RADIOHEAD"
        return ArtistReference(artist_input.raw, artist_input.label, channel_id)

    def verify_artist(self, _artist: ArtistReference) -> None:
        return None


class UnavailableRemoteApi(FakeRemoteApi):
    def resolve_artist(self, _value: str | ArtistInput) -> ArtistReference:
        raise YtMusicError("artist lookup failed")


def test_remote_validation_detects_channel_duplicates_and_waits_for_apply(tmp_path: Path) -> None:
    artists_dir = tmp_path / "artists"
    artists_dir.mkdir()
    artist_file = artists_dir / "rock.txt"
    artist_file.write_text(
        "# keep\nRadiohead\nRadiohead | https://music.youtube.com/@radiohead\nDeftones\n",
        encoding="utf-8",
    )

    report = validate_remote_artist_files(artists_dir, FakeRemoteApi())

    assert [issue.kind for issue in report.issues] == ["channel_duplicate"]
    assert report.issues[0].line_number == 3
    assert report.issues[0].channel_id == "UC-RADIOHEAD"
    assert [change.line_number for change in report.changes] == [3]
    assert "Uzak doğrulama" in format_remote_validation_report(report)[0]
    assert "@radiohead" in artist_file.read_text(encoding="utf-8")

    apply_artist_changes(report.changes)

    assert artist_file.read_text(encoding="utf-8") == "# keep\nRadiohead\nDeftones\n"


def test_remote_validation_keeps_unavailable_entries_unchanged(tmp_path: Path) -> None:
    artists_dir = tmp_path / "artists"
    artists_dir.mkdir()
    artist_file = artists_dir / "rock.txt"
    artist_file.write_text("Radiohead\n", encoding="utf-8")

    report = validate_remote_artist_files(artists_dir, UnavailableRemoteApi())

    assert report.issues[0].kind == "remote_unavailable"
    assert not report.changes
    assert artist_file.read_text(encoding="utf-8") == "Radiohead\n"
