from playlist_builder.catalog import CatalogCollector
from playlist_builder.models import Track
from playlist_builder.ytmusic import ArtistReference


class FakeCatalogApi:
    def __init__(self) -> None:
        self.list_releases_calls = 0

    def list_releases(self, reference: ArtistReference) -> list[dict[str, object]]:
        self.list_releases_calls += 1
        assert reference.channel_id == "UC-METALLICA"
        return [
            {"browseId": "ALBUM-1983", "title": "Kill 'Em All", "type": "Album", "year": "1983"},
            {"browseId": "SINGLE-1984", "title": "Creeping Death", "type": "Single", "year": "1984"},
        ]

    def get_album(self, browse_id: str) -> dict[str, object]:
        if browse_id == "ALBUM-1983":
            return {
                "title": "Kill 'Em All",
                "type": "Album",
                "year": "1983",
                "tracks": [
                    {
                        "videoId": "track-2",
                        "title": "The Four Horsemen",
                        "trackNumber": 1,
                        "duration_seconds": 331,
                    },
                    {
                        "videoId": "track-1",
                        "title": "Hit the Lights",
                        "trackNumber": 0,
                        "duration_seconds": 257,
                    },
                ],
            }
        return {
            "title": "Creeping Death",
            "type": "Single",
            "year": "1984",
            "tracks": [
                {"videoId": "single-1", "title": "Creeping Death", "trackNumber": 0}
            ],
        }


def test_collect_artist_maps_album_and_track_metadata_without_reordering() -> None:
    reference = ArtistReference("Metallica", "Metallica", "UC-METALLICA")

    tracks = CatalogCollector(FakeCatalogApi()).collect_artist(reference)

    assert tracks == [
        Track(
            video_id="track-2",
            artist="Metallica",
            album="Kill 'Em All",
            title="The Four Horsemen",
            album_type="Album",
            release_year=1983,
            track_number=1,
            source_artist_id="UC-METALLICA",
            album_id="ALBUM-1983",
            duration_seconds=331,
        ),
        Track(
            video_id="track-1",
            artist="Metallica",
            album="Kill 'Em All",
            title="Hit the Lights",
            album_type="Album",
            release_year=1983,
            track_number=0,
            source_artist_id="UC-METALLICA",
            album_id="ALBUM-1983",
            duration_seconds=257,
        ),
        Track(
            video_id="single-1",
            artist="Metallica",
            album="Creeping Death",
            title="Creeping Death",
            album_type="Single",
            release_year=1984,
            track_number=0,
            source_artist_id="UC-METALLICA",
            album_id="SINGLE-1984",
        ),
    ]


def test_collect_artist_caches_catalog_by_channel_id() -> None:
    api = FakeCatalogApi()
    collector = CatalogCollector(api)
    first_reference = ArtistReference("Metallica", "Metallica", "UC-METALLICA")
    second_reference = ArtistReference("Metallica | URL", "Metallica", "UC-METALLICA")

    first = collector.collect_artist(first_reference)
    second = collector.collect_artist(second_reference)

    assert second == first
    assert api.list_releases_calls == 1
