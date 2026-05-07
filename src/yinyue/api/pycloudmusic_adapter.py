import logging

from yinyue.api.models import Playlist, Song, Artist
from yinyue.scraper.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)

QR_STATUS_MESSAGES = {
    801: "等待扫码",
    802: "已扫码，请在手机上确认登录",
    803: "登录成功",
    800: "二维码已过期",
    8821: "请在手机上确认登录",
}


class PyCloudMusicAdapter:
    """Adapter wrapping pycloudmusic for NetEase Cloud Music API access."""

    def __init__(self, rate: float = 3.0):
        self._api = None          # Music163Api instance (set after login)
        self._logged_in = False
        self._rate_limiter = RateLimiter(rate=rate)

    @property
    def is_logged_in(self) -> bool:
        return self._logged_in

    # --- Cookie login (most reliable) ---

    def login_with_cookie(self, cookie_str: str) -> bool:
        """Login directly with a browser cookie string.

        The user copies their cookie from music.163.com after logging in
        via browser. Paste the full cookie string or just MUSIC_U=xxx.
        """
        from pycloudmusic import Music163Api

        if not cookie_str.strip():
            return False
        if "MUSIC_U=" not in cookie_str:
            cookie_str = f"MUSIC_U={cookie_str.strip()}"
        try:
            self._api = Music163Api(cookie_str)
            self._logged_in = True
            logger.info("Cookie login successful")
            return True
        except Exception as e:
            logger.error(f"Cookie login failed: {e}")
            return False

    # --- QR login (alternative) ---

    async def get_qr(self) -> dict:
        """Get QR code for login. Returns {'key': str, 'url': str}."""
        from pycloudmusic import LoginMusic163
        login = LoginMusic163()
        key, url = await login.qr_key()
        return {"key": key, "url": url}

    async def check_qr(self, key: str) -> dict:
        """Check QR scan status. Returns {'status': int, 'message': str}.

        Uses a direct HTTP call to bypass pycloudmusic's buggy _login()
        which has infinite recursion on non-200 status codes.
        """
        import aiohttp
        from pycloudmusic import Music163Api

        url = "https://music.163.com/api/login/qrcode/client/login"
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data={"key": key, "type": 1}) as resp:
                data = await resp.json(content_type=None)
                code = data.get("code", 0)

                if code == 803:
                    raw_cookies = "; ".join(
                        f"{k}={v.value}" for k, v in resp.cookies.items()
                    )
                    self._api = Music163Api(raw_cookies)
                    self._logged_in = True

                return {
                    "status": code,
                    "message": QR_STATUS_MESSAGES.get(code, f"状态码 {code}"),
                }

    # --- Data fetching ---

    async def get_playlist(self, playlist_id: int) -> Playlist:
        if not self._api:
            raise RuntimeError("Not logged in.")
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
