import json
from pathlib import Path

from playlist_builder.events import append_event


def test_append_event_writes_one_json_object_per_line(tmp_path: Path) -> None:
    log_file = tmp_path / "logs" / "run.jsonl"

    append_event(log_file, "artist_resolved", artist="Radiohead", artist_id="artist-id")

    record = json.loads(log_file.read_text(encoding="utf-8").splitlines()[0])
    assert record["event"] == "artist_resolved"
    assert record["artist"] == "Radiohead"
    assert record["artist_id"] == "artist-id"
    assert "timestamp" in record
