import asyncio
from pathlib import Path

from textual.command import CommandList, CommandPalette
from textual.widgets import DataTable, Footer, Input, Static

from playlist_builder.artists import read_artist_file
from playlist_builder.tui import PlaylistBuilderApp, run_tui


def _write_config(tmp_path: Path) -> Path:
    artists_dir = tmp_path / "artists"
    artists_dir.mkdir()
    (artists_dir / "rock.txt").write_text("Radiohead\n", encoding="utf-8")
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        "\n".join(
            (
                "auth_file: auth/oauth.json",
                "oauth_client_file: auth/client_secret.json",
                "artists_dir: artists",
                "state_dir: state",
                "cache_dir: cache",
                "logs_dir: logs",
                "playlist:",
                "  privacy: PRIVATE",
                "  max_tracks: 550",
                "  update_mode: append_only",
                "filters:",
                "  exclude_karaoke: true",
            )
        ),
        encoding="utf-8",
    )
    return config_path


def test_textual_app_loads_project_summary(tmp_path: Path) -> None:
    config_path = _write_config(tmp_path)
    app = PlaylistBuilderApp(config_path, run_fn=lambda *_args, **_kwargs: 0)

    async def scenario() -> None:
        async with app.run_test(size=(120, 40)) as pilot:
            table = app.query_one("#genres", DataTable)
            assert len(table.rows) == 1
            await pilot.click("#exit")

    asyncio.run(scenario())
    assert app.return_value == "exit"


def test_textual_command_palette_is_enabled_and_lists_app_actions(tmp_path: Path) -> None:
    config_path = _write_config(tmp_path)
    app = PlaylistBuilderApp(config_path, run_fn=lambda *_args, **_kwargs: 0)

    async def scenario() -> None:
        async with app.run_test(size=(120, 40)) as pilot:
            assert app.ENABLE_COMMAND_PALETTE is True
            assert "ctrl+p" in app.active_bindings
            await pilot.pause()
            assert len(app.query_one(Footer).query(".-command-palette")) == 1

            await pilot.press("ctrl+p")
            await pilot.pause(0.3)

            assert CommandPalette.is_open(app)
            command_list = app.screen.query_one(CommandList)
            command_text = "\n".join(str(option.prompt) for option in command_list.options)
            assert "Dry-run planını göster" in command_text
            assert "Playlistleri düzenle" in command_text

            await pilot.press("escape")
            await pilot.pause()
            assert not CommandPalette.is_open(app)

    asyncio.run(scenario())


def test_artist_editor_writes_selected_category_file(tmp_path: Path) -> None:
    config_path = _write_config(tmp_path)
    hip_hop_file = tmp_path / "artists" / "hip_hop_rap.txt"
    hip_hop_file.write_text("", encoding="utf-8")

    app = PlaylistBuilderApp(config_path, run_fn=lambda *_args, **_kwargs: 0)

    async def scenario() -> None:
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.click("#artists")
            await pilot.pause()

            path = app.screen.query_one("#artist-path", Static)
            category = app.screen.query_one("#artist-category", Static)
            assert str(category.render()) == "hip_hop_rap"
            assert str(path.render()) == f"Dosya: {Path('artists') / 'hip_hop_rap.txt'}"

            artist_input = app.screen.query_one("#artist-input", Input)
            artist_input.value = "Run-DMC"
            await pilot.click("#artist-add")
            assert read_artist_file(hip_hop_file) == []

            await pilot.click("#artist-save")
            assert read_artist_file(hip_hop_file) == ["Run-DMC"]
            await pilot.click("#artist-close")

    asyncio.run(scenario())


def test_artist_editor_layout_fits_common_terminal_sizes(tmp_path: Path) -> None:
    config_path = _write_config(tmp_path)

    async def scenario() -> None:
        for size in ((80, 24), (120, 35)):
            app = PlaylistBuilderApp(config_path, run_fn=lambda *_args, **_kwargs: 0)
            async with app.run_test(size=size) as pilot:
                await pilot.click("#artists")
                await pilot.pause()

                screen = app.screen
                footer = screen.query_one(Footer).region
                body = screen.query_one("#editor-body").region
                columns = screen.query_one("#editor-columns").region
                artist_input = screen.query_one("#artist-input").region
                actions = screen.query_one("#editor-actions").region
                status = screen.query_one("#editor-status").region

                assert body.bottom <= footer.y
                assert columns.bottom <= artist_input.y
                assert artist_input.bottom <= actions.y
                assert status.bottom <= footer.y
                for button_id in (
                    "playlist-new",
                    "playlist-rename",
                    "playlist-delete",
                    "artist-add",
                    "artist-edit",
                    "artist-delete",
                    "artist-save",
                    "artist-close",
                ):
                    assert screen.query_one(f"#{button_id}").region.right <= size[0]

                screen.dismiss("closed")

    asyncio.run(scenario())


def test_playlist_editor_can_create_rename_and_delete_playlist_file(tmp_path: Path) -> None:
    config_path = _write_config(tmp_path)
    artists_dir = tmp_path / "artists"
    app = PlaylistBuilderApp(config_path, run_fn=lambda *_args, **_kwargs: 0)

    async def scenario() -> None:
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.click("#artists")
            await pilot.pause()

            await pilot.press("n")
            app.screen.query_one("#artist-input", Input).value = "Focus Mix"
            await pilot.press("enter")
            assert (artists_dir / "Focus Mix.txt").is_file()

            await pilot.click("#artist-categories")
            await pilot.press("m")
            app.screen.query_one("#artist-input", Input).value = "Focus"
            await pilot.press("enter")
            assert not (artists_dir / "Focus Mix.txt").exists()
            assert (artists_dir / "Focus.txt").is_file()

            await pilot.click("#artist-categories")
            await pilot.press("p")
            await pilot.pause()
            await pilot.press("y")
            await pilot.pause()
            assert not (artists_dir / "Focus.txt").exists()

            await pilot.click("#artist-close")

    asyncio.run(scenario())


def test_artist_editor_can_edit_and_delete_before_saving(tmp_path: Path) -> None:
    config_path = _write_config(tmp_path)
    artist_file = tmp_path / "artists" / "rock.txt"
    app = PlaylistBuilderApp(config_path, run_fn=lambda *_args, **_kwargs: 0)

    async def scenario() -> None:
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.click("#artists")
            await pilot.pause()
            screen = app.screen
            artist_table = screen.query_one("#artist-list", DataTable)
            artist_table.move_cursor(row=0, column=0, animate=False)
            await pilot.click("#artist-edit")
            screen.query_one("#artist-input", Input).value = "The Smile"
            await pilot.press("enter")

            assert read_artist_file(artist_file) == ["Radiohead"]
            screen.query_one("#artist-input", Input).value = "Deftones"
            await pilot.click("#artist-add")
            artist_table.move_cursor(row=0, column=0, animate=False)
            await pilot.click("#artist-delete")
            await pilot.click("#artist-save")

            assert read_artist_file(artist_file) == ["The Smile"]
            await pilot.click("#artist-close")

    asyncio.run(scenario())


def test_textual_layout_fits_common_terminal_sizes(tmp_path: Path) -> None:
    config_path = _write_config(tmp_path)

    async def scenario() -> None:
        for size in ((80, 24), (100, 30), (120, 35)):
            app = PlaylistBuilderApp(config_path, run_fn=lambda *_args, **_kwargs: 0)
            async with app.run_test(size=size) as pilot:
                body = app.query_one("#body").region
                genres = app.query_one("#genres").region
                output = app.query_one("#output").region
                footer = app.query_one(Footer).region
                sidebar = app.query_one("#sidebar")

                assert genres.bottom <= output.y
                assert output.bottom <= footer.y
                assert output.bottom <= body.bottom
                assert sidebar.region.bottom <= body.bottom

                if size == (120, 35):
                    assert app.query_one("#refresh").region.bottom <= sidebar.region.bottom
                    assert app.query_one("#exit").region.bottom <= sidebar.region.bottom

                if size == (80, 24):
                    assert sidebar.virtual_size.height > sidebar.region.height
                    sidebar.scroll_end(animate=False, immediate=True, force=True)
                    await pilot.pause()
                    assert app.query_one("#exit").region.bottom <= sidebar.region.bottom

                app.exit("layout-check")

    asyncio.run(scenario())


def test_textual_app_runs_dry_run_in_worker(tmp_path: Path) -> None:
    config_path = _write_config(tmp_path)
    calls: list[bool] = []

    def fake_run(
        _config_path: Path,
        *,
        dry_run: bool,
        progress_fn: object,
    ) -> int:
        calls.append(dry_run)
        progress_fn("test progress")
        return 0

    app = PlaylistBuilderApp(config_path, run_fn=fake_run)

    async def scenario() -> None:
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.click("#dry-run")
            await pilot.pause(0.2)

    asyncio.run(scenario())
    assert calls == [True]
    assert app._busy is False


def test_run_tui_restarts_after_oauth(tmp_path: Path) -> None:
    config_path = _write_config(tmp_path)
    actions = iter(["oauth", "exit"])
    oauth_calls: list[Path] = []
    output: list[str] = []

    class FakeApp:
        def __init__(self, _config_path: Path, *, run_fn: object) -> None:
            self.run_fn = run_fn

        def run(self) -> str:
            return next(actions)

    def fake_setup(config: Path) -> int:
        oauth_calls.append(config)
        return 0

    assert (
        run_tui(
            config_path,
            output_fn=output.append,
            setup_oauth_fn=fake_setup,
            app_factory=FakeApp,
        )
        == 0
    )
    assert oauth_calls == [config_path]
    assert output == ["OAuth kurulumu başlıyor...", "OAuth kurulumu tamamlandı."]
