from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from .auth import AuthError, setup_oauth as create_oauth_file
from .artists import read_artist_entry_lists
from .catalog import CatalogCollector
from .config import ConfigError, load_config
from .events import append_event
from .playlists import PlaylistReport, PlaylistWriter
from .processing import prepare_tracks
from .state import (
    ArtistAlias,
    BuildState,
    StateError,
    artist_alias_is_fresh,
    load_state,
    save_state,
)
from .validation import (
    ArtistFileChange,
    apply_artist_changes,
    format_change_plan,
    format_remote_validation_report,
    format_validation_report,
    validate_format_files,
    validate_remote_artist_files,
)
from .ytmusic import (
    ArtistInput,
    ArtistReference,
    YtMusicAdapter,
    YtMusicError,
    canonical_artist_key,
    normalize_artist_name,
    parse_artist_input,
)


def _state_key(name: str) -> str:
    return name.casefold().strip()


def _emit(message: str, progress_fn: Callable[[str], None] | None) -> None:
    if progress_fn is None:
        print(message)
    else:
        progress_fn(message)


def _configure_console_encoding() -> None:
    """Keep Turkish status/error messages printable on legacy Windows consoles."""

    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (OSError, ValueError):
            continue


def _log_report(log_path: Path, genre: str, report: PlaylistReport) -> None:
    event = "playlist_created" if report.created else "playlist_updated"
    append_event(
        log_path,
        event,
        genre=genre,
        title=report.title,
        playlist_id=report.playlist_id,
        added=list(report.added_video_ids),
        skipped=list(report.skipped_video_ids),
        manually_removed=list(report.manually_removed_video_ids),
    )


def _confirm_changes(
    changes: tuple[ArtistFileChange, ...],
    *,
    output_fn: Callable[[str], None],
    input_fn: Callable[[str], str],
) -> bool:
    for line in format_change_plan(changes):
        output_fn(line)
    try:
        answer = input_fn("Değişiklikler uygulansın mı? [y/N]: ")
    except EOFError:
        output_fn("Onay alınamadı; değişiklikler uygulanmadı.")
        return False
    return answer.strip().casefold() in {"y", "yes", "e", "evet"}


def _validation_status(report: object, *, changes_applied: bool) -> int:
    issues = getattr(report, "issues")
    if not issues:
        return 0
    if not changes_applied:
        return 1
    changes = getattr(report, "changes")
    fixed_lines = {(change.path, change.line_number) for change in changes}
    return 0 if all((issue.path, issue.line_number) in fixed_lines for issue in issues) else 1


def validate_format(
    config_path: Path,
    *,
    output_fn: Callable[[str], None] | None = None,
    input_fn: Callable[[str], str] = input,
) -> int:
    if output_fn is None:
        _configure_console_encoding()
        output_fn = print
    config = load_config(config_path)
    report = validate_format_files(config.artists_dir)
    for line in format_validation_report(report):
        output_fn(line)
    changes_applied = False
    if report.changes:
        if _confirm_changes(report.changes, output_fn=output_fn, input_fn=input_fn):
            apply_artist_changes(report.changes)
            changes_applied = True
            output_fn(f"{len(report.changes)} güvenli düzeltme uygulandı.")
        else:
            output_fn("Değişiklikler uygulanmadı.")
    return _validation_status(report, changes_applied=changes_applied)


def validate_remote(
    config_path: Path,
    *,
    output_fn: Callable[[str], None] | None = None,
    input_fn: Callable[[str], str] = input,
) -> int:
    if output_fn is None:
        _configure_console_encoding()
        output_fn = print
    config = load_config(config_path)
    if config.auth_file is None:
        raise ConfigError("auth_file is required for remote artist validation")
    api = YtMusicAdapter.from_auth(
        config.auth_file,
        oauth_client_file=config.oauth_client_file,
    )
    report = validate_remote_artist_files(config.artists_dir, api)
    for line in format_remote_validation_report(report):
        output_fn(line)
    changes_applied = False
    if report.changes:
        if _confirm_changes(report.changes, output_fn=output_fn, input_fn=input_fn):
            apply_artist_changes(report.changes)
            changes_applied = True
            output_fn(f"{len(report.changes)} güvenli düzeltme uygulandı.")
        else:
            output_fn("Değişiklikler uygulanmadı.")
    return _validation_status(report, changes_applied=changes_applied)


def _artist_alias_keys(artist_input: ArtistInput, artist: ArtistReference) -> set[str]:
    keys = {
        canonical_artist_key(artist_input),
        f"channel:{artist.channel_id}",
        f"name:{normalize_artist_name(artist.display_name)}",
    }
    if artist_input.display_name:
        keys.add(f"name:{normalize_artist_name(artist_input.display_name)}")
    if artist_input.handle:
        keys.add(f"handle:{artist_input.handle.casefold()}")
    return keys


def _cached_artist_alias(
    state: BuildState,
    artist_input: ArtistInput,
    max_age_days: int,
) -> ArtistReference | None:
    alias = state.artist_aliases.get(canonical_artist_key(artist_input))
    if alias is None or not artist_alias_is_fresh(alias, max_age_days):
        return None
    return ArtistReference(artist_input.raw, alias.display_name, alias.channel_id)


def _remember_artist_alias(
    state: BuildState,
    artist_input: ArtistInput,
    artist: ArtistReference,
) -> None:
    alias = ArtistAlias(
        channel_id=artist.channel_id,
        display_name=artist.display_name,
        resolved_at=datetime.now(timezone.utc).isoformat(),
    )
    for key in _artist_alias_keys(artist_input, artist):
        state.artist_aliases[key] = alias


def run(
    config_path: Path,
    *,
    dry_run: bool = False,
    progress_fn: Callable[[str], None] | None = None,
) -> int:
    config = load_config(config_path)
    if config.auth_file is None:
        raise ConfigError("auth_file is required to build YouTube Music playlists")

    artist_lists = read_artist_entry_lists(config.artists_dir)
    state_path = config.state_dir / "build_state.json"
    log_path = config.logs_dir / "build.jsonl"
    state = load_state(state_path)
    api = YtMusicAdapter.from_auth(
        config.auth_file,
        oauth_client_file=config.oauth_client_file,
    )
    collector = CatalogCollector(api)
    writer = PlaylistWriter(api)
    errors = 0

    for genre, artist_names in artist_lists.items():
        if progress_fn is not None:
            progress_fn(f"{genre}: {len(artist_names)} sanatçı işlenecek")
        raw_tracks = []
        seen_input_keys: set[str] = set()
        seen_channel_ids: set[str] = set()
        for entry in artist_names:
            artist_name = entry.value
            try:
                artist_input = parse_artist_input(artist_name)
                input_key = canonical_artist_key(artist_input)
                if input_key in seen_input_keys:
                    append_event(
                        log_path,
                        "artist_duplicate",
                        genre=genre,
                        artist=artist_name,
                        line_number=entry.line_number,
                        duplicate_key=input_key,
                        reason="same normalized input",
                    )
                    if progress_fn is not None:
                        progress_fn(
                            f"{genre} / {artist_name}: duplicate, atlandı "
                            f"(satır {entry.line_number})"
                        )
                    continue
                seen_input_keys.add(input_key)

                artist = _cached_artist_alias(
                    state,
                    artist_input,
                    config.artist_cache_ttl_days,
                )
                key = _state_key(artist_name)
                channel_id = state.artist_ids.get(key)
                if artist is None and channel_id is not None:
                    artist = ArtistReference(artist_name, artist_input.label, channel_id)
                elif artist is None:
                    artist = api.resolve_artist(artist_input)
                    if not dry_run:
                        state.artist_ids[key] = artist.channel_id
                        _remember_artist_alias(state, artist_input, artist)

                if artist.channel_id in seen_channel_ids:
                    append_event(
                        log_path,
                        "artist_duplicate",
                        genre=genre,
                        artist=artist_name,
                        line_number=entry.line_number,
                        channel_id=artist.channel_id,
                        reason="same resolved channel_id",
                    )
                    if progress_fn is not None:
                        progress_fn(
                            f"{genre} / {artist_name}: aynı sanatçı, katalog atlandı "
                            f"(satır {entry.line_number})"
                        )
                    continue
                seen_channel_ids.add(artist.channel_id)

                artist_tracks = collector.collect_artist(artist)
                raw_tracks.extend(artist_tracks)
                append_event(
                    log_path,
                    "artist_collected",
                    genre=genre,
                    artist=artist_name,
                    channel_id=artist.channel_id,
                    track_count=len(artist_tracks),
                )
                if progress_fn is not None:
                    progress_fn(f"{genre} / {artist_name}: {len(artist_tracks)} parça")
            except YtMusicError as error:
                errors += 1
                append_event(
                    log_path,
                    "artist_not_found",
                    genre=genre,
                    artist=artist_name,
                    error=str(error),
                )
                if progress_fn is not None:
                    progress_fn(f"{genre} / {artist_name}: bulunamadı")

        chunks = prepare_tracks(raw_tracks, config.filters)
        reports = writer.sync_genre(
            genre,
            chunks,
            state,
            privacy=config.playlist.privacy,
            dry_run=dry_run,
        )
        for report in reports:
            _log_report(log_path, genre, report)
        if not dry_run:
            save_state(state_path, state)
        _emit(
            f"{genre}: {sum(len(report.added_video_ids) for report in reports)} new track(s)",
            progress_fn,
        )

    if not dry_run:
        save_state(state_path, state)
    return 1 if errors else 0


def setup_oauth(config_path: Path) -> int:
    config = load_config(config_path)
    if config.auth_file is None:
        raise ConfigError("auth_file is required for OAuth setup")
    if config.oauth_client_file is None:
        raise ConfigError("oauth_client_file is required for OAuth setup")

    auth_file = create_oauth_file(config.oauth_client_file, config.auth_file)
    print(f"OAuth tamamlandı: {auth_file}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build YouTube Music RAW playlists.")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config.yaml"),
        help="Path to config.yaml (default: config.yaml)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Read and plan changes without creating or updating playlists",
    )
    parser.add_argument(
        "--tui",
        action="store_true",
        help="Open the interactive terminal menu",
    )
    parser.add_argument(
        "--setup-oauth",
        action="store_true",
        help="Create the local YouTube Music OAuth token",
    )
    validation_group = parser.add_mutually_exclusive_group()
    validation_group.add_argument(
        "--validate-format",
        action="store_true",
        help="Validate artist-file format and local duplicates without using the network",
    )
    validation_group.add_argument(
        "--validate-remote",
        action="store_true",
        help="Resolve artists through YouTube Music and detect channel duplicates",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    _configure_console_encoding()
    args = build_parser().parse_args(argv)
    try:
        if args.setup_oauth:
            return setup_oauth(args.config)
        if args.validate_format:
            return validate_format(args.config)
        if args.validate_remote:
            return validate_remote(args.config)
        if args.tui:
            from .tui import run_tui

            return run_tui(args.config)
        return run(args.config, dry_run=args.dry_run)
    except (AuthError, ConfigError, StateError, YtMusicError, OSError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2
