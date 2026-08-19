import asyncio
from pathlib import Path

from textual.widgets import DataTable, Footer

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
