from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .artists import ArtistEntry, artist_file_paths, read_artist_entries
from .ytmusic import YtMusicError, canonical_artist_key, parse_artist_input


@dataclass(frozen=True, slots=True)
class ArtistValidationIssue:
    genre: str
    path: Path
    line_number: int
    value: str
    kind: str
    message: str
    duplicate_of_line: int | None = None


@dataclass(frozen=True, slots=True)
class ArtistValidationReport:
    files_checked: int
    entries_checked: int
    issues: tuple[ArtistValidationIssue, ...]

    @property
    def is_valid(self) -> bool:
        return not self.issues


def validate_artist_files(directory: Path) -> ArtistValidationReport:
    issues: list[ArtistValidationIssue] = []
    files_checked = 0
    entries_checked = 0

    for genre, path in artist_file_paths(directory).items():
        files_checked += 1
        seen: dict[str, ArtistEntry] = {}
        for entry in read_artist_entries(path):
            entries_checked += 1
            try:
                artist_input = parse_artist_input(entry.value)
                key = canonical_artist_key(artist_input)
            except YtMusicError as error:
                issues.append(
                    ArtistValidationIssue(
                        genre=genre,
                        path=path,
                        line_number=entry.line_number,
                        value=entry.value,
                        kind="invalid",
                        message=str(error),
                    )
                )
                continue

            previous = seen.get(key)
            if previous is not None:
                issues.append(
                    ArtistValidationIssue(
                        genre=genre,
                        path=path,
                        line_number=entry.line_number,
                        value=entry.value,
                        kind="duplicate",
                        message=(
                            f"duplicate input; first occurrence is line {previous.line_number}"
                        ),
                        duplicate_of_line=previous.line_number,
                    )
                )
                continue
            seen[key] = entry

    return ArtistValidationReport(files_checked, entries_checked, tuple(issues))


def format_validation_report(report: ArtistValidationReport) -> list[str]:
    if report.is_valid:
        return [
            f"Doğrulama başarılı: {report.files_checked} dosya, "
            f"{report.entries_checked} sanatçı girdisi; sorun yok."
        ]

    lines = [
        f"Doğrulama: {len(report.issues)} sorun bulundu "
        f"({report.files_checked} dosya, {report.entries_checked} girdi)."
    ]
    for issue in report.issues:
        lines.append(
            f"- {issue.path.name}:{issue.line_number} [{issue.kind}] "
            f"{issue.value} — {issue.message}"
        )
    return lines
