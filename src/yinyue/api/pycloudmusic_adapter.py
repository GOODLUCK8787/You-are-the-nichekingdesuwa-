import asyncio
import logging
from typing import Optional

from yinyue.api.models import Playlist, Song, Artist, NicheScores
from yinyue.scraper.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)


class PyCloudMusicAdapter:
    """Adapter wrapping pycloudmusic for NetEase Cloud Music API access."""

    def __init__(self, rate: float = 3.0):
        self._api = None          # Music163Api instance (set after login)
        self._login = None        # LoginMusic163 instance
        self._logged_in = False
        self._rate_limiter = RateLimiter(rate=rate)

    @property
    def is_logged_in(self) -> bool:
        return self._logged_in

    # --- Login ---

    async def get_qr(self) -> dict:
        """Get QR code for login. Returns {'key': str, 'url': str}."""
        from pycloudmusic import LoginMusic163
        self._login = LoginMusic163()
        key, url = await self._login.qr_key()
        return {"key": key, "url": url}

    async def check_qr(self, key: str) -> dict:
        """Check QR scan status. Returns {'status': int, 'nickname': str}.
        Status codes: 801=waiting, 802=scanned, 803=logged in, 800=expired.
        """
        if not self._login:
            raise RuntimeError("Call get_qr() first")
        from pycloudmusic import Music163BadCode
        try:
            cookie = await self._login.qr_check(key)
            # Success: cookie returned (code 803)
            if not self._api:
                from pycloudmusic import Music163Api
                self._api = Music163Api(cookie)
            self._logged_in = True
            return {"status": 803, "nickname": "已登录"}
        except Music163BadCode as err:
            return {"status": err.code, "nickname": ""}

    # --- Data fetching ---

    async def get_playlist(self, playlist_id: int) -> Playlist:
        """Fetch playlist metadata + song list."""
        if not self._api:
            raise RuntimeError("Not logged in. Call check_qr() first.")

        await self._rate_limiter.acquire()
        raw = await self._api.playlist(playlist_id)

        playlist = Playlist(
            netease_id=raw.id,
            name=raw.name,
            description=raw.description or "",
            owner_name=raw.user_str,
            owner_id=raw.user.get("userId") if raw.user else None,
            song_count=len(raw.music_list),
            play_count=raw.play_count or 0,
            share_count=0,
            tags=raw.tags if raw.tags else [],
            create_time=raw.create_time,
            url=f"https://music.163.com/playlist?id={playlist_id}",
            songs=[],
        )

        # Convert raw tracks to Song models
        for track in raw.music_list:
            artists = [Artist(netease_id=ar["id"], name=ar["name"]) for ar in track.get("ar", [])]
            song = Song(
                netease_id=track["id"],
                name=track.get("name", ""),
                artists=artists,
                album_name=track.get("al", {}).get("name", ""),
                album_id=track.get("al", {}).get("id"),
                duration_ms=track.get("dt", 0),
                popularity=float(track.get("pop", 0)),
                genre_tags=[],
            )
            playlist.songs.append(song)

        logger.info(f"Fetched playlist: {playlist.name} ({playlist.song_count} songs)")
        return playlist

    async def get_song_details(self, song_ids: list[int]) -> list[Song]:
        """Fetch detailed song info for a list of song IDs."""
        if not self._api:
            raise RuntimeError("Not logged in.")

        songs = []
        for song_id in song_ids:
            await self._rate_limiter.acquire()
            try:
                music = await self._api.music(song_id)
                artists = [Artist(netease_id=a["id"], name=a["name"]) for a in music.artist]
                song = Song(
                    netease_id=music.id,
                    name=music.name_str,
                    artists=artists,
                    album_name=music.album_str,
                    album_id=music.album_data.get("id"),
                    duration_ms=music.duration_ms,
                    popularity=float(getattr(music, "pop", 0)),
                    genre_tags=[],
                )
                songs.append(song)
            except Exception as e:
                logger.warning(f"Failed to fetch song {song_id}: {e}")

        return songs
