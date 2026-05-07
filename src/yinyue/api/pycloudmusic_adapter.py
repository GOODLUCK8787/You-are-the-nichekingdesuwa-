import logging
import os
import subprocess
import tempfile
from pathlib import Path

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
        self._browser_process = None
        self._browser_cookie_file = None

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

    # --- QR login (pure aiohttp, bypasses pycloudmusic entirely) ---

    # Headers mimicking browser to avoid NetEase rejecting requests
    _QR_HEADERS = {
        "Accept": "*/*",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Content-Type": "application/x-www-form-urlencoded",
        "Referer": "https://music.163.com/",
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
    }

    async def get_qr(self) -> dict:
        """Get QR code key and URL. Uses direct HTTP to avoid pycloudmusic bugs."""
        import aiohttp

        url = "https://music.163.com/api/login/qrcode/unikey"
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url, data={"type": 1}, headers=self._QR_HEADERS
            ) as resp:
                data = await resp.json(content_type=None)
                key = data.get("unikey", "")
                if not key:
                    raise RuntimeError(f"获取二维码key失败: {data}")
                return {
                    "key": key,
                    "url": f"https://music.163.com/login?codekey={key}",
                }

    async def check_qr(self, key: str) -> dict:
        """Check QR scan status. Returns {'status': int, 'message': str}.

        Uses direct HTTP to bypass pycloudmusic's buggy _login()
        which has infinite recursion on non-200 status codes.
        """
        import aiohttp
        from pycloudmusic import Music163Api

        url = "https://music.163.com/api/login/qrcode/client/login"
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url, data={"key": key, "type": 1}, headers=self._QR_HEADERS
            ) as resp:
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

    # --- Browser login (Playwright, most reliable) ---

    def launch_browser_login(self) -> subprocess.Popen | None:
        """Launch a Playwright browser window for official NetEase QR login.

        Returns the subprocess handle, or None if Playwright is not installed.
        """
        try:
            from playwright.sync_api import sync_playwright  # noqa: F401
        except ImportError:
            logger.error("Playwright not installed")
            return None

        fd, self._browser_cookie_file = tempfile.mkstemp(
            suffix=".txt", prefix="net_ease_cookies_"
        )
        os.close(fd)

        script_path = Path(__file__).resolve().parent / "browser_login.py"
        self._browser_process = subprocess.Popen(
            ["python", str(script_path), self._browser_cookie_file],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        logger.info("Browser login process launched")
        return self._browser_process

    def finish_browser_login(self) -> bool:
        """Check if browser login completed and set up the API client.

        Returns True if login was successful.
        """
        if self._browser_cookie_file is None:
            return False

        cookie_path = Path(self._browser_cookie_file)
        if not cookie_path.exists() or cookie_path.stat().st_size == 0:
            return False

        cookie_str = cookie_path.read_text(encoding="utf-8").strip()
        if not cookie_str or "MUSIC_U=" not in cookie_str:
            return False

        from pycloudmusic import Music163Api

        try:
            self._api = Music163Api(cookie_str)
            self._logged_in = True
            logger.info("Browser login successful")
            # Clean up temp file
            cookie_path.unlink(missing_ok=True)
            self._browser_cookie_file = None
            self._browser_process = None
            return True
        except Exception as e:
            logger.error(f"Browser login failed: {e}")
            return False

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
