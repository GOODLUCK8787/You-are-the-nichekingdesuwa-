import logging
from yinyue.api.client import NetEaseClient
from yinyue.api.models import Playlist, Song
from yinyue.db.database import save_playlist, save_song, playlist_exists, init_db

logger = logging.getLogger(__name__)


class ScraperPipeline:
    """Orchestrates playlist + song data collection and persistence."""

    def __init__(self, client: NetEaseClient):
        self.client = client
        init_db()  # Ensure DB is ready

    async def run(self, url: str, force_refresh: bool = False) -> Playlist:
        """
        Full pipeline: parse URL → fetch playlist → save to DB.

        Returns the Playlist model (all songs included).
        Uses cached data if available, unless force_refresh=True.
        """
        playlist_id = NetEaseClient.parse_playlist_url(url)
        if playlist_id is None:
            raise ValueError(f"无法解析歌单链接: {url}")

        # Check cache
        if not force_refresh and playlist_exists(playlist_id):
            logger.info(f"Playlist {playlist_id} already cached, using cache")
            playlist = await self.client.get_playlist(playlist_id)
            return playlist

        # Fetch fresh data
        logger.info(f"Fetching playlist {playlist_id} ...")
        playlist = await self.client.get_playlist(playlist_id)

        # Save playlist metadata
        save_playlist({
            "netease_id": playlist.netease_id,
            "name": playlist.name,
            "description": playlist.description,
            "owner_name": playlist.owner_name,
            "owner_id": playlist.owner_id,
            "song_count": playlist.song_count,
            "play_count": playlist.play_count,
            "share_count": playlist.share_count,
            "comment_count": playlist.comment_count,
            "tags": ",".join(playlist.tags) if playlist.tags else "",
            "create_time": playlist.create_time,
            "update_time": playlist.update_time,
            "url": playlist.url,
        })

        # Save each song
        for song in playlist.songs:
            save_song(0, {
                "netease_id": song.netease_id,
                "name": song.name,
                "artists": [{"id": a.netease_id, "name": a.name} for a in song.artists],
                "album_name": song.album_name,
                "album_id": song.album_id,
                "duration_ms": song.duration_ms,
                "popularity": song.popularity,
                "genre_tags": song.genre_tags,
            })

        logger.info(f"Saved playlist '{playlist.name}' ({playlist.song_count} songs) to DB")
        return playlist
