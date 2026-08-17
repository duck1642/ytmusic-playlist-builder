from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from .auth import AuthError
from .config import ConfigError
from .state import StateError
from .ytmusic import YtMusicError


def run_tui(
    config_path: Path,
    *,
    input_fn: Callable[[str], str] = input,
    output_fn: Callable[[str], None] = print,
    run_fn: Callable[..., int] | None = None,
    setup_oauth_fn: Callable[[Path], int] | None = None,
) -> int:
    """Run the small interactive menu used by the project launcher."""
    if run_fn is None:
        from .cli import run

        run_fn = run
    if setup_oauth_fn is None:
        from .cli import setup_oauth

        setup_oauth_fn = setup_oauth

    while True:
        output_fn("")
        output_fn("YouTube Music Playlist Builder")
        output_fn("1) OAuth kurulumu")
        output_fn("2) Dry-run planını göster")
        output_fn("3) Playlist oluşturma/güncelleme")
        output_fn("4) Çıkış")
        try:
            choice = input_fn("Seçim: ").strip()
        except (EOFError, KeyboardInterrupt):
            output_fn("")
            return 0

        if choice == "4":
            return 0
        if choice not in {"1", "2", "3"}:
            output_fn("Geçersiz seçim.")
            continue

        if choice == "1":
            output_fn("OAuth kurulumu başlıyor...")
            try:
                status = setup_oauth_fn(config_path)
            except (AuthError, ConfigError, OSError) as error:
                output_fn(f"Hata: {error}")
                continue
            if status == 0:
                output_fn("OAuth kurulumu tamamlandı.")
            else:
                output_fn(f"OAuth kurulumu hata koduyla tamamlandı: {status}")
            continue

        dry_run = choice == "2"
        output_fn("Dry-run başlıyor..." if dry_run else "Playlist oluşturma/güncelleme başlıyor...")
        try:
            status = run_fn(config_path, dry_run=dry_run)
        except (AuthError, ConfigError, StateError, YtMusicError, OSError) as error:
            output_fn(f"Hata: {error}")
            continue

        if status == 0:
            output_fn("İşlem tamamlandı.")
        else:
            output_fn(f"İşlem hata koduyla tamamlandı: {status}")
