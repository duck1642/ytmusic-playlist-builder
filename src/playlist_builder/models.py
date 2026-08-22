from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True, slots=True)
class Track:
    video_id: str
    artist: str
    album: str
    title: str
    album_type: str = "Album"
    release_date: date | None = None
    release_year: int | None = None
    track_number: int | None = None
    source_artist_id: str | None = None
    album_id: str | None = None
    duration_seconds: int | None = None
