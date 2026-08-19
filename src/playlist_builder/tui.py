from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from textual.app import App, ComposeResult, SystemCommand
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen, Screen
from textual.widgets import Button, DataTable, Footer, Header, Input, Log, Static

from .artists import (
    artist_file_paths,
    create_playlist_file,
    delete_playlist_file,
    read_artist_lists,
    rename_playlist_file,
    write_artist_file,
)
from .auth import AuthError
from .config import ConfigError, load_config
from .playlists import genre_label


RunFunction = Callable[..., int]
SetupOAuthFunction = Callable[[Path], int]
AppFactory = Callable[..., "PlaylistBuilderApp"]


class ConfirmPlaylistDeleteScreen(ModalScreen[bool]):
    """Confirm a local playlist-file deletion before changing the project."""

    CSS = """
    ConfirmPlaylistDeleteScreen {
        align: center middle;
        background: $background 90%;
    }

    #delete-dialog {
        width: 52;
        height: auto;
        padding: 1 2;
        border: round $error;
        background: $panel;
    }

    #delete-dialog Button {
        width: 1fr;
        margin: 1 1 0 0;
    }
    """
    BINDINGS = [
        ("y", "confirm_delete", "Sil"),
        ("n", "cancel_delete", "Vazgeç"),
        ("escape", "cancel_delete", "Vazgeç"),
    ]

    def __init__(self, playlist_name: str) -> None:
        super().__init__()
        self.playlist_name = playlist_name

    def compose(self) -> ComposeResult:
        with Vertical(id="delete-dialog"):
            yield Static(f'"{self.playlist_name}" playlist dosyası silinsin mi?')
            yield Static("YouTube Music'teki mevcut playlist silinmez.")
            with Horizontal():
                yield Button("Sil", id="confirm-delete", variant="error")
                yield Button("Vazgeç", id="cancel-delete")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "confirm-delete":
            self.action_confirm_delete()
        elif event.button.id == "cancel-delete":
            self.action_cancel_delete()

    def action_confirm_delete(self) -> None:
        self.dismiss(True)

    def action_cancel_delete(self) -> None:
        self.dismiss(False)


class ArtistEditorScreen(ModalScreen[str]):
    """Manage playlist files and their artist lists without leaving the TUI."""

    CSS = """
    ModalScreen {
        background: $background;
    }

    #editor-body {
        height: 1fr;
        padding: 1;
    }

    #editor-heading {
        margin: 0 0 1 0;
    }

    #editor-columns {
        height: 1fr;
        min-height: 8;
    }

    #editor-categories {
        width: 34;
        min-width: 28;
        margin: 0 1 0 0;
        padding: 1;
        border: round $panel;
    }

    #category-actions {
        height: auto;
        margin: 1 0 0 0;
    }

    #category-actions Button {
        width: 100%;
        margin: 0 0 1 0;
    }

    #editor-artists {
        width: 1fr;
        padding: 1;
        border: round $panel;
    }

    #artist-categories,
    #artist-list {
        height: 1fr;
        min-height: 4;
    }

    #artist-path {
        height: auto;
        margin: 0 0 1 0;
        color: $text-muted;
    }

    #artist-input {
        margin: 1 0;
    }

    #editor-actions {
        height: 3;
    }

    #editor-actions Button {
        width: 1fr;
        min-width: 8;
        margin: 0 1 0 0;
    }

    #editor-status {
        height: 2;
        padding: 0 1;
    }
    """
    BINDINGS = [
        Binding("n", "new_playlist", "Yeni playlist"),
        Binding("m", "rename_playlist", "Ad değiştir"),
        Binding("p", "delete_playlist", "Playlist sil"),
        Binding("a", "focus_artist_input", "Ekle"),
        Binding("e", "edit_artist", "Düzenle", show=False),
        Binding("x", "delete_artist", "Sil", show=False),
        Binding("s", "save_artists", "Kaydet"),
        Binding("r", "reload_artists", "Diskten yükle", show=False),
        Binding("escape", "close_editor", "Kapat"),
    ]

    def __init__(self, config_path: Path, *, initial_genre: str | None = None) -> None:
        super().__init__()
        self.config_path = config_path
        self.initial_genre = initial_genre
        self._artists: dict[str, list[str]] = {}
        self._artist_paths: dict[str, Path] = {}
        self._selected_genre: str | None = None
        self._dirty_genres: set[str] = set()
        self._editing_index: int | None = None
        self._playlist_input_mode: str | None = None

    def compose(self) -> ComposeResult:
        yield Header(icon=" ")
        with Vertical(id="editor-body"):
            yield Static("Playlistleri ve sanatçıları düzenle", id="editor-heading", classes="section-title")
            with Horizontal(id="editor-columns"):
                with Vertical(id="editor-categories"):
                    yield Static("Playlistler", classes="section-title")
                    yield DataTable(id="artist-categories")
                    with Vertical(id="category-actions"):
                        yield Button("Yeni", id="playlist-new", variant="primary")
                        yield Button("Ad değiştir", id="playlist-rename")
                        yield Button("Sil", id="playlist-delete", variant="error")
                with Vertical(id="editor-artists"):
                    yield Static(id="artist-category", classes="section-title")
                    yield Static(id="artist-path")
                    yield DataTable(id="artist-list")
            yield Input(
                placeholder="Sanatçı adı yazın; Enter ile ekleyin veya düzenleyin",
                id="artist-input",
            )
            with Horizontal(id="editor-actions"):
                yield Button("Ekle", id="artist-add", variant="primary")
                yield Button("Düzenle", id="artist-edit")
                yield Button("Sil", id="artist-delete", variant="error")
                yield Button("Kaydet", id="artist-save", variant="success")
                yield Button("Kapat", id="artist-close")
            yield Static(id="editor-status")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#artist-categories", DataTable).add_columns("Playlist", "Sanatçı")
        self.query_one("#artist-list", DataTable).add_column("Sanatçı")
        self._reload_from_disk()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        actions = {
            "playlist-new": self.action_new_playlist,
            "playlist-rename": self.action_rename_playlist,
            "playlist-delete": self.action_delete_playlist,
            "artist-add": self._add_artist,
            "artist-edit": self.action_edit_artist,
            "artist-delete": self.action_delete_artist,
            "artist-save": self.action_save_artists,
            "artist-close": self.action_close_editor,
        }
        action = actions.get(event.button.id or "")
        if action is not None:
            action()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id != "artist-input":
            return
        if self._playlist_input_mode is not None:
            self._submit_playlist_name()
        elif self._editing_index is None:
            self._add_artist()
        else:
            self._apply_artist_edit()

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if event.data_table.id == "artist-categories":
            self._select_genre(event.row_key.value)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        if event.data_table.id == "artist-categories":
            self._select_genre(event.row_key.value)

    def action_focus_artist_input(self) -> None:
        if self._selected_genre is not None:
            self._playlist_input_mode = None
            self.query_one("#artist-input", Input).focus()

    def action_new_playlist(self) -> None:
        if self._dirty_genres:
            self._set_editor_status("Kaydedilmemiş sanatçı değişikliği var; önce Kaydet'e basın.")
            return
        self._playlist_input_mode = "create"
        self._editing_index = None
        artist_input = self.query_one("#artist-input", Input)
        artist_input.value = ""
        artist_input.focus()
        self._set_editor_status("Yeni playlist adı yazın; Enter ile oluşturun.")

    def action_rename_playlist(self) -> None:
        if self._dirty_genres:
            self._set_editor_status("Kaydedilmemiş sanatçı değişikliği var; önce Kaydet'e basın.")
            return
        if self._selected_genre is None:
            self._set_editor_status("Adını değiştirmek için bir playlist seçin.")
            return
        self._playlist_input_mode = "rename"
        self._editing_index = None
        artist_input = self.query_one("#artist-input", Input)
        artist_input.value = self._selected_genre
        artist_input.select_all()
        artist_input.focus()
        self._set_editor_status("Yeni playlist adı yazın; Enter ile yeniden adlandırın.")

    def action_delete_playlist(self) -> None:
        if self._dirty_genres:
            self._set_editor_status("Kaydedilmemiş sanatçı değişikliği var; önce Kaydet'e basın.")
            return
        if self._selected_genre is None:
            self._set_editor_status("Silmek için bir playlist seçin.")
            return
        self.app.push_screen(
            ConfirmPlaylistDeleteScreen(self._selected_genre),
            self._after_playlist_delete_confirmation,
        )

    def _submit_playlist_name(self) -> None:
        mode = self._playlist_input_mode
        name = self.query_one("#artist-input", Input).value.strip()
        if mode is None:
            return
        try:
            config = load_config(self.config_path)
            if mode == "create":
                path = create_playlist_file(config.artists_dir, name)
                message = f"Playlist oluşturuldu: {path.stem}"
            else:
                if self._selected_genre is None:
                    self._set_editor_status("Yeniden adlandırmak için bir playlist seçin.")
                    return
                path = rename_playlist_file(config.artists_dir, self._selected_genre, name)
                message = f"Playlist yeniden adlandırıldı: {path.stem}"
        except (ConfigError, OSError, ValueError) as error:
            self._set_editor_status(f"Playlist işlemi başarısız: {error}")
            return

        self._selected_genre = path.stem
        self._playlist_input_mode = None
        self.query_one("#artist-input", Input).value = ""
        self._reload_from_disk()
        self._set_editor_status(message)

    def _after_playlist_delete_confirmation(self, confirmed: bool | None) -> None:
        if not confirmed or self._selected_genre is None:
            return
        deleted_name = self._selected_genre
        try:
            config = load_config(self.config_path)
            delete_playlist_file(config.artists_dir, deleted_name)
        except (ConfigError, OSError, ValueError) as error:
            self._set_editor_status(f"Playlist silinemedi: {error}")
            return

        self._selected_genre = None
        self._reload_from_disk()
        self._set_editor_status(f"Playlist dosyası silindi: {deleted_name}")

    def action_edit_artist(self) -> None:
        self._playlist_input_mode = None
        index = self._selected_artist_index()
        if index is None:
            self._set_editor_status("Düzenlemek için bir sanatçı seçin.")
            return
        self._editing_index = index
        artist = self._artists[self._selected_genre or ""][index]
        artist_input = self.query_one("#artist-input", Input)
        artist_input.value = artist
        artist_input.focus()
        self._set_editor_status(f"Düzenleniyor: {artist}. Enter ile kaydedin.")

    def action_delete_artist(self) -> None:
        self._playlist_input_mode = None
        index = self._selected_artist_index()
        if index is None:
            self._set_editor_status("Silmek için bir sanatçı seçin.")
            return
        genre = self._selected_genre or ""
        artist = self._artists[genre].pop(index)
        self._dirty_genres.add(genre)
        self._editing_index = None
        self._render_artist_list()
        self._set_editor_status(f"{artist} silindi. Değişikliği korumak için Kaydet'e basın.")

    def action_save_artists(self) -> None:
        if not self._dirty_genres:
            self._set_editor_status("Kaydedilecek değişiklik yok.")
            return
        try:
            for genre in sorted(self._dirty_genres):
                write_artist_file(self._artist_paths[genre], self._artists[genre])
        except (KeyError, OSError) as error:
            self._set_editor_status(f"Kaydetme hatası: {error}")
            return
        self._dirty_genres.clear()
        self._editing_index = None
        self._playlist_input_mode = None
        self._render_category_table()
        self._set_editor_status("Değişiklikler dosyalara kaydedildi.")

    def action_reload_artists(self) -> None:
        if self._dirty_genres:
            self._set_editor_status("Kaydedilmemiş değişiklik var; önce Kaydet'e basın.")
            return
        self._reload_from_disk()

    def action_close_editor(self) -> None:
        if self._dirty_genres:
            self._set_editor_status("Kaydedilmemiş değişiklik var; önce Kaydet'e basın.")
            return
        self.dismiss("closed")

    def _reload_from_disk(self) -> None:
        try:
            config = load_config(self.config_path)
            self._artist_paths = artist_file_paths(config.artists_dir)
            self._artists = read_artist_lists(config.artists_dir)
        except (ConfigError, OSError) as error:
            self._artists = {}
            self._artist_paths = {}
            self._set_editor_status(f"Yapılandırma hatası: {error}")
            self._render_category_table()
            return

        self._dirty_genres.clear()
        self._editing_index = None
        self._playlist_input_mode = None
        self.query_one("#artist-input", Input).value = ""
        self._render_category_table()
        if not self._artists:
            self._set_editor_status("Düzenlenecek sanatçı dosyası bulunamadı.")

    def _render_category_table(self) -> None:
        table = self.query_one("#artist-categories", DataTable)
        table.clear()
        genres = list(self._artists)
        for genre in genres:
            table.add_row(genre_label(genre), str(len(self._artists[genre])), key=genre)

        if not genres:
            self._selected_genre = None
            self.query_one("#artist-category", Static).update("Playlist seçilmedi")
            self.query_one("#artist-path", Static).update("")
            self.query_one("#artist-list", DataTable).clear()
            return

        selected = self._selected_genre
        if selected not in genres:
            selected = self.initial_genre if self.initial_genre in genres else genres[0]
        table.move_cursor(row=genres.index(selected), column=0, animate=False)
        self._select_genre(selected)

    def _select_genre(self, genre: str) -> None:
        if genre not in self._artists:
            return
        self._selected_genre = genre
        self._editing_index = None
        self._playlist_input_mode = None
        path = self._artist_paths[genre]
        try:
            display_path = path.relative_to(self.config_path.parent)
        except ValueError:
            display_path = path
        self.query_one("#artist-category", Static).update(genre_label(genre))
        self.query_one("#artist-path", Static).update(f"Dosya: {display_path}")
        self._render_artist_list()

    def _render_artist_list(self) -> None:
        table = self.query_one("#artist-list", DataTable)
        table.clear()
        if self._selected_genre is None:
            return
        for index, artist in enumerate(self._artists[self._selected_genre]):
            table.add_row(artist, key=str(index))
        self._update_editor_status()

    def _selected_artist_index(self) -> int | None:
        if self._selected_genre is None:
            return None
        index = self.query_one("#artist-list", DataTable).cursor_row
        if index < 0 or index >= len(self._artists[self._selected_genre]):
            return None
        return index

    def _add_artist(self) -> None:
        if self._selected_genre is None:
            self._set_editor_status("Önce bir playlist seçin.")
            return
        name = self.query_one("#artist-input", Input).value.strip()
        if not name or name.startswith("#"):
            self._set_editor_status("Geçerli bir sanatçı adı yazın.")
            return
        artists = self._artists[self._selected_genre]
        if any(artist.casefold() == name.casefold() for artist in artists):
            self._set_editor_status(f"Sanatçı zaten listede: {name}")
            return
        artists.append(name)
        artists.sort(key=str.casefold)
        self._dirty_genres.add(self._selected_genre)
        self._editing_index = None
        self._playlist_input_mode = None
        self.query_one("#artist-input", Input).value = ""
        self._render_category_table()
        self._set_editor_status(f"{name} eklendi. Değişikliği korumak için Kaydet'e basın.")

    def _apply_artist_edit(self) -> None:
        if self._selected_genre is None or self._editing_index is None:
            return
        name = self.query_one("#artist-input", Input).value.strip()
        if not name or name.startswith("#"):
            self._set_editor_status("Geçerli bir sanatçı adı yazın.")
            return
        artists = self._artists[self._selected_genre]
        index = self._editing_index
        if any(
            position != index and artist.casefold() == name.casefold()
            for position, artist in enumerate(artists)
        ):
            self._set_editor_status(f"Sanatçı zaten listede: {name}")
            return
        artists[index] = name
        artists.sort(key=str.casefold)
        self._dirty_genres.add(self._selected_genre)
        self._editing_index = None
        self._playlist_input_mode = None
        self.query_one("#artist-input", Input).value = ""
        self._render_category_table()
        self._set_editor_status(f"Sanatçı güncellendi: {name}")

    def _set_editor_status(self, message: str) -> None:
        self.query_one("#editor-status", Static).update(message)

    def _update_editor_status(self) -> None:
        if self._selected_genre is None:
            return
        state = "kaydedilmemiş değişiklik var" if self._selected_genre in self._dirty_genres else "kaydedildi"
        count = len(self._artists[self._selected_genre])
        self._set_editor_status(f"{count} sanatçı — {state}")


class PlaylistBuilderApp(App[str]):
    """Small keyboard-driven terminal UI around the existing build workflow."""

    TITLE = "YouTube Music Playlist Builder"
    ENABLE_COMMAND_PALETTE = True
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
        min-height: 6;
        margin: 0 0 1 0;
        padding: 0 1;
        border: round $panel;
    }

    #genres {
        height: 11;
        min-height: 9;
        max-height: 11;
        margin: 0 0 1 0;
        border: round $panel;
    }

    #output {
        height: 1fr;
        min-height: 5;
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

    #sidebar #exit {
        margin: 0;
    }

    #sidebar #refresh {
        margin-bottom: 0;
    }
    """
    BINDINGS = [
        ("d", "dry_run", "Plan"),
        ("b", "build", "Oluştur"),
        ("a", "edit_artists", "Playlistler"),
        ("r", "refresh", "Yenile"),
        Binding(
            "ctrl+p",
            "command_palette",
            "Komutlar",
            show=False,
            key_display="Ctrl+P",
            priority=True,
            tooltip="Komut paletini aç",
        ),
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
        self._genre_keys: list[str] = []

    def compose(self) -> ComposeResult:
        yield Header(icon=" ")
        with Horizontal(id="body"):
            with VerticalScroll(id="sidebar"):
                yield Static("Durum", classes="section-title")
                yield Static(id="status")
                yield Button("Dry-run planı", id="dry-run", variant="primary")
                yield Button("Build / güncelle", id="build", variant="success")
                yield Button("Playlistleri düzenle", id="artists")
                yield Button("OAuth kurulumu", id="oauth")
                yield Button("Yenile", id="refresh")
                yield Button("Çıkış", id="exit", variant="error")
            with Vertical(id="content"):
                yield Static("Playlistler", classes="section-title")
                yield DataTable(id="genres")
                yield Static("Çıktı", classes="section-title")
                yield Log(id="output")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#genres", DataTable)
        table.add_columns("Playlist", "Sanatçı", "Durum")
        self._refresh_summary()
        self._write_log("Hazır. Dry-run için D, gerçek işlem için B tuşuna basın.")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id == "dry-run":
            self.action_dry_run()
        elif button_id == "build":
            self.action_build()
        elif button_id == "artists":
            self.action_edit_artists()
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

    def action_edit_artists(self) -> None:
        if self._busy:
            return
        self.push_screen(
            ArtistEditorScreen(self.config_path, initial_genre=self._selected_genre()),
            self._after_artist_editor,
        )

    def action_quit_app(self) -> None:
        if self._busy:
            self._write_log("İşlem devam ederken çıkış yapılamaz.")
            return
        self.exit("exit")

    def get_system_commands(self, screen: Screen):
        """Add the app's primary actions to Textual's native command palette."""
        yield from super().get_system_commands(screen)
        if isinstance(screen, ArtistEditorScreen):
            return
        yield SystemCommand(
            "Dry-run planını göster",
            "Playlist oluşturmadan planı ve bulunacak parçaları gösterir.",
            self.action_dry_run,
        )
        yield SystemCommand(
            "Playlist oluştur / güncelle",
            "Sanatçı dosyalarından playlistleri oluşturur veya günceller.",
            self.action_build,
        )
        yield SystemCommand(
            "Playlistleri düzenle",
            "Playlist dosyalarını ve sanatçı listelerini düzenler.",
            self.action_edit_artists,
        )
        yield SystemCommand(
            "Projeyi yenile",
            "Playlist dosyalarını yeniden okuyup özeti günceller.",
            self.action_refresh,
        )

    def _request_oauth(self) -> None:
        if self._busy:
            return
        self._write_log("OAuth terminal akışını başlatmak için arayüz kapatılıyor...")
        self.exit("oauth")

    def _refresh_summary(self) -> None:
        status = self.query_one("#status", Static)
        table = self.query_one("#genres", DataTable)
        table.clear()
        self._genre_keys = []

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
            self._genre_keys.append(genre)
            table.add_row(
                genre_label(genre),
                str(len(artists)),
                "Hazır" if artists else "Boş",
                key=genre,
            )

    def _selected_genre(self) -> str | None:
        table = self.query_one("#genres", DataTable)
        row = table.cursor_row
        if row < 0 or row >= len(self._genre_keys):
            return None
        return self._genre_keys[row]

    def _after_artist_editor(self, _result: str | None) -> None:
        self._refresh_summary()
        self._write_log("Playlist dosyaları yenilendi.")

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
        for button_id in ("dry-run", "build", "artists", "oauth", "refresh", "exit"):
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
