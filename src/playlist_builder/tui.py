from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from .config import ConfigError
from .state import StateError
from .ytmusic import YtMusicError


def run_tui(
    config_path: Path,
    *,
    input_fn: Callable[[str], str] = input,
    output_fn: Callable[[str], None] = print,
    run_fn: Callable[..., int] | None = None,
) -> int:
    """Run the small interactive menu used by the project launcher."""
    if run_fn is None:
        from .cli import run

        run_fn = run

    while True:
        output_fn("")
        output_fn("YouTube Music Playlist Builder")
        output_fn("1) Dry-run planını göster")
        output_fn("2) Playlist oluşturma/güncelleme")
        output_fn("3) Çıkış")
        try:
            choice = input_fn("Seçim: ").strip()
        except (EOFError, KeyboardInterrupt):
            output_fn("")
            return 0

        if choice == "3":
            return 0
        if choice not in {"1", "2"}:
            output_fn("Geçersiz seçim.")
            continue

        dry_run = choice == "1"
        output_fn("Dry-run başlıyor..." if dry_run else "Playlist oluşturma/güncelleme başlıyor...")
        try:
            status = run_fn(config_path, dry_run=dry_run)
        except (ConfigError, StateError, YtMusicError, OSError) as error:
            output_fn(f"Hata: {error}")
            continue

        if status == 0:
            output_fn("İşlem tamamlandı.")
        else:
            output_fn(f"İşlem hata koduyla tamamlandı: {status}")
