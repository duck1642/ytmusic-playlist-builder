from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, DataTable, Footer, Header, Log, Static

from .artists import read_artist_lists
from .auth import AuthError
from .config import ConfigError, load_config
from .playlists import genre_label


RunFunction = Callable[..., int]
SetupOAuthFunction = Callable[[Path], int]
AppFactory = Callable[..., "PlaylistBuilderApp"]


class PlaylistBuilderApp(App[str]):
    """Small keyboard-driven terminal UI around the existing build workflow."""

    TITLE = "YouTube Music Playlist Builder"
    CSS = """
    Screen {
        layout: vertical;
    }

    #body {
        height: 1fr;
    }

    #sidebar {
        width: 30;
        min-width: 26;
        padding: 1;
        border: round $accent;
    }

    #content {
        width: 1fr;
        padding: 1;
    }

    #status {
        height: auto;
        min-height: 8;
        margin: 0 0 1 0;
        padding: 1;
        border: round $panel;
    }

    #genres {
        height: 1fr;
        min-height: 8;
        margin: 0 0 1 0;
        border: round $panel;
    }

    #output {
        height: 1fr;
        min-height: 8;
        border: round $panel;
    }

    .section-title {
        text-style: bold;
        margin: 0 0 1 0;
    }

    Button {
        width: 100%;
        margin: 0 0 1 0;
    }
    """
    BINDINGS = [
        ("d", "dry_run", "Dry-run"),
        ("b", "build", "Build"),
        ("r", "refresh", "Yenile"),
        ("q", "quit_app", "Çıkış"),
    ]

    def __init__(
        self,
        config_path: Path,
        *,
        run_fn: RunFunction,
    ) -> None:
        super().__init__()
        self.config_path = config_path
        self.run_fn = run_fn
        self._busy = False

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="body"):
            with Vertical(id="sidebar"):
                yield Static("Durum", classes="section-title")
                yield Static(id="status")
                yield Button("Dry-run planını göster", id="dry-run", variant="primary")
                yield Button("Playlist oluştur / güncelle", id="build", variant="success")
                yield Button("OAuth kurulumu", id="oauth")
                yield Button("Bilgileri yenile", id="refresh")
                yield Button("Çıkış", id="exit", variant="error")
            with Vertical(id="content"):
                yield Static("Kategoriler", classes="section-title")
                yield DataTable(id="genres")
                yield Static("Çıktı", classes="section-title")
                yield Log(id="output")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#genres", DataTable)
        table.add_columns("Kategori", "Sanatçı", "Durum")
        self._refresh_summary()
        self._write_log("Hazır. Dry-run için D, gerçek işlem için B tuşuna basın.")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id == "dry-run":
            self.action_dry_run()
        elif button_id == "build":
            self.action_build()
        elif button_id == "oauth":
            self._request_oauth()
        elif button_id == "refresh":
            self.action_refresh()
        elif button_id == "exit":
            self.action_quit_app()

    def action_dry_run(self) -> None:
        self._start_operation(dry_run=True)

    def action_build(self) -> None:
        self._start_operation(dry_run=False)

    def action_refresh(self) -> None:
        if self._busy:
            return
        self._refresh_summary()
        self._write_log("Proje bilgileri yenilendi.")

    def action_quit_app(self) -> None:
        if self._busy:
            self._write_log("İşlem devam ederken çıkış yapılamaz.")
            return
        self.exit("exit")

    def _request_oauth(self) -> None:
        if self._busy:
            return
        self._write_log("OAuth terminal akışını başlatmak için arayüz kapatılıyor...")
        self.exit("oauth")

    def _refresh_summary(self) -> None:
        status = self.query_one("#status", Static)
        table = self.query_one("#genres", DataTable)
        table.clear()

        try:
            config = load_config(self.config_path)
            artist_lists = read_artist_lists(config.artists_dir)
        except (ConfigError, OSError) as error:
            status.update(f"Yapılandırma hatası:\n{error}")
            table.add_row("-", "-", "Hata")
            return

        auth_ready = config.auth_file is not None and config.auth_file.is_file()
        filter_names = [
            name
            for name, enabled in (
                ("live", config.filters.exclude_live),
                ("remix", config.filters.exclude_remix),
                ("remaster", config.filters.exclude_remaster),
                ("deluxe", config.filters.exclude_deluxe),
                ("karaoke", config.filters.exclude_karaoke),
            )
            if enabled
        ]
        filters = ", ".join(filter_names) if filter_names else "yok"
        status.update(
            "\n".join(
                (
                    f"OAuth: {'hazır' if auth_ready else 'eksik'}",
                    f"Playlist: {config.playlist.privacy}",
                    f"Parça limiti: {config.playlist.max_tracks}",
                    f"Filtreler: {filters}",
                )
            )
        )

        if not artist_lists:
            table.add_row("-", "0", "Sanatçı dosyası yok")
            return
        for genre, artists in artist_lists.items():
            table.add_row(
                genre_label(genre),
                str(len(artists)),
                "Hazır" if artists else "Boş",
            )

    def _start_operation(self, *, dry_run: bool) -> None:
        if self._busy:
            return
        self._busy = True
        self._set_action_buttons(disabled=True)
        operation = "Dry-run" if dry_run else "Playlist oluşturma/güncelleme"
        self._write_log(f"{operation} başlıyor...")
        self.run_worker(
            lambda: self._execute_operation(dry_run),
            name="playlist-build",
            group="playlist-build",
            exclusive=True,
            thread=True,
        )

    def _execute_operation(self, dry_run: bool) -> None:
        try:
            status = self.run_fn(
                self.config_path,
                dry_run=dry_run,
                progress_fn=self._report_from_worker,
            )
        except Exception as error:
            self.call_from_thread(self._finish_operation, None, str(error))
            return
        self.call_from_thread(self._finish_operation, status, None)

    def _report_from_worker(self, message: str) -> None:
        self.call_from_thread(self._write_log, message)

    def _finish_operation(self, status: int | None, error: str | None) -> None:
        self._busy = False
        self._set_action_buttons(disabled=False)
        if error is not None:
            self._write_log(f"Hata: {error}")
        elif status == 0:
            self._write_log("İşlem tamamlandı.")
        else:
            self._write_log("İşlem tamamlandı; bazı sanatçılar bulunamamış olabilir.")
        self._refresh_summary()

    def _set_action_buttons(self, *, disabled: bool) -> None:
        for button_id in ("dry-run", "build", "oauth", "refresh", "exit"):
            self.query_one(f"#{button_id}", Button).disabled = disabled

    def _write_log(self, message: str) -> None:
        self.query_one("#output", Log).write_line(message)


def run_tui(
    config_path: Path,
    *,
    input_fn: Callable[[str], str] = input,
    output_fn: Callable[[str], None] = print,
    run_fn: RunFunction | None = None,
    setup_oauth_fn: SetupOAuthFunction | None = None,
    app_factory: AppFactory | None = None,
) -> int:
    """Run the Textual UI and keep the blocking OAuth flow outside it."""
    if run_fn is None:
        from .cli import run

        run_fn = run
    if setup_oauth_fn is None:
        from .cli import setup_oauth

        setup_oauth_fn = setup_oauth
    if app_factory is None:
        app_factory = PlaylistBuilderApp

    del input_fn  # Kept for compatibility with the previous TUI API.
    while True:
        app = app_factory(config_path, run_fn=run_fn)
        result = app.run()
        if result != "oauth":
            return 0

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
