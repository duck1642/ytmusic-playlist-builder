from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .artists import ArtistEntry, apply_artist_line_changes, artist_file_paths, read_artist_entries
from .ytmusic import YtMusicError, canonical_artist_key, parse_artist_input


@dataclass(frozen=True, slots=True)
class ArtistFileChange:
    """One approved-safe, line-preserving change to an artist file."""

    path: Path
    line_number: int
    old_value: str
    replacement: str | None
    reason: str


@dataclass(frozen=True, slots=True)
class ArtistValidationIssue:
    genre: str
    path: Path
    line_number: int
    value: str
    kind: str
    message: str
    duplicate_of_line: int | None = None
    suggestion: str | None = None
    channel_id: str | None = None


@dataclass(frozen=True, slots=True)
class ArtistValidationReport:
    files_checked: int
    entries_checked: int
    issues: tuple[ArtistValidationIssue, ...]
    changes: tuple[ArtistFileChange, ...] = ()

    @property
    def is_valid(self) -> bool:
        return not self.issues


@dataclass(frozen=True, slots=True)
class RemoteArtistValidationReport:
    files_checked: int
    entries_checked: int
    resolved_entries: int
    issues: tuple[ArtistValidationIssue, ...]
    changes: tuple[ArtistFileChange, ...] = ()

    @property
    def is_valid(self) -> bool:
        return not self.issues


def _duplicate_change(entry: ArtistEntry, *, reason: str) -> ArtistFileChange:
    return ArtistFileChange(
        path=entry.path,
        line_number=entry.line_number,
        old_value=entry.value,
        replacement=None,
        reason=reason,
    )


def _invalid_suggestion(value: str) -> str:
    if "|" in value:
        return "URL kısmını /@handle veya /channel/<channel-id> biçiminde düzeltin."
    return "YouTube Music URL'sini /@handle veya /channel/<channel-id> biçiminde yazın."


def validate_format_files(directory: Path) -> ArtistValidationReport:
    """Validate artist-file syntax and local canonical duplicates without network access."""

    issues: list[ArtistValidationIssue] = []
    changes: list[ArtistFileChange] = []
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
                        suggestion=_invalid_suggestion(entry.value),
                    )
                )
                continue

            previous = seen.get(key)
            if previous is not None:
                reason = f"Aynı normalize edilmiş girdi; ilk satır korunacak ({previous.line_number})."
                issues.append(
                    ArtistValidationIssue(
                        genre=genre,
                        path=path,
                        line_number=entry.line_number,
                        value=entry.value,
                        kind="duplicate",
                        message=f"duplicate input; first occurrence is line {previous.line_number}",
                        duplicate_of_line=previous.line_number,
                        suggestion="İlk satır korunarak bu satır kaldırılabilir.",
                    )
                )
                changes.append(_duplicate_change(entry, reason=reason))
                continue
            seen[key] = entry

    return ArtistValidationReport(
        files_checked,
        entries_checked,
        tuple(issues),
        tuple(changes),
    )


def validate_remote_artist_files(
    directory: Path,
    api: Any,
) -> RemoteArtistValidationReport:
    """Resolve artist entries and detect duplicate YouTube Music channel IDs.

    This function performs network-backed checks through the supplied adapter. It
    never writes artist files or persistent build state.
    """

    format_report = validate_format_files(directory)
    issues = list(format_report.issues)
    changes_by_line = {
        (change.path, change.line_number): change for change in format_report.changes
    }
    resolved_entries = 0

    for genre, path in artist_file_paths(directory).items():
        seen_input_keys: set[str] = set()
        seen_channels: dict[str, ArtistEntry] = {}
        for entry in read_artist_entries(path):
            try:
                artist_input = parse_artist_input(entry.value)
                input_key = canonical_artist_key(artist_input)
            except YtMusicError:
                continue

            if input_key in seen_input_keys:
                continue
            seen_input_keys.add(input_key)

            try:
                artist = api.resolve_artist(artist_input)
                api.verify_artist(artist)
            except YtMusicError as error:
                issues.append(
                    ArtistValidationIssue(
                        genre=genre,
                        path=path,
                        line_number=entry.line_number,
                        value=entry.value,
                        kind="remote_unavailable",
                        message=str(error),
                        suggestion=(
                            "Sanatçı adı/URL'sini YouTube Music'te manuel kontrol edin; "
                            "bu satır otomatik değiştirilmeyecek."
                        ),
                    )
                )
                continue

            resolved_entries += 1
            previous = seen_channels.get(artist.channel_id)
            if previous is not None:
                reason = (
                    f"Aynı channel ID ({artist.channel_id}); ilk satır korunacak "
                    f"({previous.line_number})."
                )
                issues.append(
                    ArtistValidationIssue(
                        genre=genre,
                        path=path,
                        line_number=entry.line_number,
                        value=entry.value,
                        kind="channel_duplicate",
                        message=(
                            f"same resolved channel_id as line {previous.line_number}: "
                            f"{artist.channel_id}"
                        ),
                        duplicate_of_line=previous.line_number,
                        suggestion="İlk satır korunarak bu satır kaldırılabilir.",
                        channel_id=artist.channel_id,
                    )
                )
                changes_by_line.setdefault(
                    (path, entry.line_number),
                    _duplicate_change(entry, reason=reason),
                )
                continue
            seen_channels[artist.channel_id] = entry

    return RemoteArtistValidationReport(
        format_report.files_checked,
        format_report.entries_checked,
        resolved_entries,
        tuple(issues),
        tuple(changes_by_line.values()),
    )


def _format_issue(issue: ArtistValidationIssue) -> str:
    line = (
        f"- {issue.path.name}:{issue.line_number} [{issue.kind}] "
        f"{issue.value} — {issue.message}"
    )
    if issue.suggestion:
        line += f" Öneri: {issue.suggestion}"
    return line


def format_validation_report(report: ArtistValidationReport) -> list[str]:
    """Format the local, network-free validation report."""

    if report.is_valid:
        return [
            f"Format doğrulaması başarılı: {report.files_checked} dosya, "
            f"{report.entries_checked} sanatçı girdisi; sorun yok."
        ]

    lines = [
        f"Format doğrulaması: {len(report.issues)} sorun bulundu "
        f"({report.files_checked} dosya, {report.entries_checked} girdi)."
    ]
    lines.extend(_format_issue(issue) for issue in report.issues)
    if report.changes:
        lines.append(
            f"Güvenli düzeltme adayı: {len(report.changes)} duplicate satırı; "
            "onay verilmeden dosyaya yazılmaz."
        )
    return lines


def format_remote_validation_report(report: RemoteArtistValidationReport) -> list[str]:
    """Format the API-backed validation report."""

    if report.is_valid:
        return [
            f"Uzak doğrulama başarılı: {report.files_checked} dosya, "
            f"{report.entries_checked} girdi, {report.resolved_entries} çözüm; sorun yok."
        ]

    lines = [
        f"Uzak doğrulama: {len(report.issues)} sorun bulundu "
        f"({report.files_checked} dosya, {report.entries_checked} girdi, "
        f"{report.resolved_entries} çözüm)."
    ]
    lines.extend(_format_issue(issue) for issue in report.issues)
    if report.changes:
        lines.append(
            f"Güvenli düzeltme adayı: {len(report.changes)} duplicate satırı; "
            "onay verilmeden dosyaya yazılmaz."
        )
    return lines


def format_change_plan(
    changes: tuple[ArtistFileChange, ...] | list[ArtistFileChange],
) -> list[str]:
    if not changes:
        return ["Uygulanacak güvenli düzeltme yok."]
    lines = ["Güvenli düzeltme planı:"]
    for change in changes:
        action = "silinecek" if change.replacement is None else f"→ {change.replacement}"
        lines.append(
            f"- {change.path.name}:{change.line_number} {action}: "
            f"{change.old_value} — {change.reason}"
        )
    return lines


def apply_artist_changes(
    changes: tuple[ArtistFileChange, ...] | list[ArtistFileChange],
) -> None:
    """Apply only the already-presented, line-addressed changes."""

    # Do not apply a stale approval to a line that changed after validation.
    for change in changes:
        with change.path.open("r", encoding="utf-8", newline="") as source:
            lines = source.read().splitlines(keepends=True)
        if change.line_number > len(lines):
            raise ValueError(
                f"Artist file changed after validation: {change.path}:{change.line_number}"
            )
        current_value = lines[change.line_number - 1].rstrip("\r\n").strip()
        if current_value != change.old_value:
            raise ValueError(
                f"Artist file changed after validation: {change.path}:{change.line_number}"
            )

    grouped: dict[Path, dict[int, str | None]] = defaultdict(dict)
    for change in changes:
        grouped[change.path][change.line_number] = change.replacement
    for path, line_changes in grouped.items():
        apply_artist_line_changes(path, line_changes)
