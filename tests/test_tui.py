from pathlib import Path

from playlist_builder.tui import run_tui


def test_tui_routes_dry_run_and_build_choices() -> None:
    choices = iter(["1", "2", "3", "4"])
    calls: list[tuple[Path, bool]] = []
    oauth_calls: list[Path] = []
    output: list[str] = []

    def fake_run(config_path: Path, *, dry_run: bool) -> int:
        calls.append((config_path, dry_run))
        return 0

    def fake_setup_oauth(config_path: Path) -> int:
        oauth_calls.append(config_path)
        return 0

    result = run_tui(
        Path("config.yaml"),
        input_fn=lambda _prompt: next(choices),
        output_fn=output.append,
        run_fn=fake_run,
        setup_oauth_fn=fake_setup_oauth,
    )

    assert result == 0
    assert calls == [(Path("config.yaml"), True), (Path("config.yaml"), False)]
    assert oauth_calls == [Path("config.yaml")]
    assert any("OAuth" in line for line in output)
    assert any("Dry-run" in line for line in output)
    assert any("oluşturma/güncelleme" in line for line in output)


def test_tui_ignores_invalid_choice_and_exits_on_eof() -> None:
    choices = iter(["x"])
    output: list[str] = []

    def input_fn(_prompt: str) -> str:
        try:
            return next(choices)
        except StopIteration as error:
            raise EOFError from error

    assert run_tui(Path("config.yaml"), input_fn=input_fn, output_fn=output.append) == 0
    assert any("Geçersiz" in line for line in output)
