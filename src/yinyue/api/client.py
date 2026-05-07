import logging
from enum import Enum
from typing import Optional

from yinyue.api.pycloudmusic_adapter import PyCloudMusicAdapter
from yinyue.api.models import Playlist, Song

logger = logging.getLogger(__name__)


class ApiBackend(str, Enum):
    PYCLOUDMUSIC = "pycloudmusic"


class NetEaseClient:
    """Unified NetEase Cloud Music API client."""

    def __init__(self, backend: ApiBackend = ApiBackend.PYCLOUDMUSIC, rate: float = 3.0):
        if backend == ApiBackend.PYCLOUDMUSIC:
            self._adapter = PyCloudMusicAdapter(rate=rate)
        else:
            raise ValueError(f"Unsupported backend: {backend}")
        self._backend = backend

    @property
    def is_logged_in(self) -> bool:
        return self._adapter.is_logged_in

    # --- Login ---

    def login_with_cookie(self, cookie_str: str) -> bool:
        """Login directly with a browser cookie string."""
        return self._adapter.login_with_cookie(cookie_str)

    async def get_qr(self) -> dict:
        return await self._adapter.get_qr()

    async def check_qr(self, key: str) -> dict:
        return await self._adapter.check_qr(key)

    # --- Data ---

    async def get_playlist(self, playlist_id: int) -> Playlist:
        return await self._adapter.get_playlist(playlist_id)

    async def get_song_details(self, song_ids: list[int]) -> list[Song]:
        return await self._adapter.get_song_details(song_ids)

    @staticmethod
    def parse_playlist_url(url: str) -> Optional[int]:
        """Extract playlist ID from a NetEase Cloud Music URL."""
        import re
        match = re.search(r"playlist[^/]*[?&]id=(\d+)", url)
        if match:
            return int(match.group(1))
        match = re.search(r"/playlist/(\d+)", url)
        if match:
            return int(match.group(1))
        return None
