from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from .artists import read_artist_lists
from .catalog import CatalogCollector
from .config import ConfigError, load_config
from .events import append_event
from .playlists import PlaylistReport, PlaylistWriter
from .processing import prepare_tracks
from .state import BuildState, StateError, load_state, save_state
from .ytmusic import ArtistReference, YtMusicAdapter, YtMusicError


def _state_key(name: str) -> str:
    return name.casefold().strip()


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


def run(config_path: Path, *, dry_run: bool = False) -> int:
    config = load_config(config_path)
    if config.auth_file is None:
        raise ConfigError("auth_file is required to build YouTube Music playlists")

    artist_lists = read_artist_lists(config.artists_dir)
    state_path = config.state_dir / "build_state.json"
    log_path = config.logs_dir / "build.jsonl"
    state = load_state(state_path)
    api = YtMusicAdapter.from_auth(config.auth_file)
    collector = CatalogCollector(api)
    writer = PlaylistWriter(api)
    errors = 0

    for genre, artist_names in artist_lists.items():
        raw_tracks = []
        for artist_name in artist_names:
            key = _state_key(artist_name)
            try:
                channel_id = state.artist_ids.get(key)
                if channel_id is not None:
                    artist = ArtistReference(artist_name, artist_name, channel_id)
                else:
                    artist = api.resolve_artist(artist_name)
                    if not dry_run:
                        state.artist_ids[key] = artist.channel_id
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
            except YtMusicError as error:
                errors += 1
                append_event(
                    log_path,
                    "artist_not_found",
                    genre=genre,
                    artist=artist_name,
                    error=str(error),
                )

        chunks = prepare_tracks(raw_tracks, config.filters, config.playlist.max_tracks)
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
        print(f"{genre}: {sum(len(report.added_video_ids) for report in reports)} new track(s)")

    if not dry_run:
        save_state(state_path, state)
    return 1 if errors else 0


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
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return run(args.config, dry_run=args.dry_run)
    except (ConfigError, StateError, YtMusicError, OSError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2
