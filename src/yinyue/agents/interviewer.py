import json
import logging
from yinyue.llm.base import LLMClient
from yinyue.prompts.interviewer import INTERVIEWER_PROMPT
from yinyue.api.models import Playlist

logger = logging.getLogger(__name__)


class InterviewerAgent:
    """Generates Sakiko-style questions based on playlist content."""

    def __init__(self, llm: LLMClient):
        self.llm = llm

    async def generate_questions(self, playlist: Playlist, niche_summary: str = "") -> list[dict]:
        """Generate 3-5 questions about the playlist. Returns [{"id": "q1", "question": "...", "tone": "..."}]."""
        user_content = self._build_context(playlist, niche_summary)
        response = await self.llm.chat(
            messages=[
                {"role": "system", "content": INTERVIEWER_PROMPT},
                {"role": "user", "content": user_content},
            ],
            temperature=0.8,
        )
        return self._parse_questions(response)

    def _build_context(self, playlist: Playlist, niche_summary: str) -> str:
        songs_preview = "\n".join(
            f"  - {s.name} / {', '.join(a.name for a in s.artists)} "
            f"(播放量:{s.play_count}, 热度:{s.popularity})"
            for s in playlist.songs[:20]
        )
        more = f"\n  ... 还有 {len(playlist.songs) - 20} 首" if len(playlist.songs) > 20 else ""

        return f"""请审视这份歌单：

名称：{playlist.name}
创建者：{playlist.owner_name}
歌曲数：{playlist.song_count}首
描述：{playlist.description or '（无）'}
标签：{', '.join(playlist.tags) if playlist.tags else '（无）'}

歌曲列表：
{songs_preview}{more}

{niche_summary}

请根据以上内容，生成3-5个问题反问用户。"""

    def _parse_questions(self, response: str) -> list[dict]:
        """Try to parse JSON from LLM response, fallback to plain text."""
        try:
            cleaned = response.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1]
                if cleaned.endswith("```"):
                    cleaned = cleaned[:-3]
            questions = json.loads(cleaned)
            if isinstance(questions, list):
                return questions
        except (json.JSONDecodeError, Exception):
            pass

        # Fallback: split by numbered questions
        logger.warning("Failed to parse questions JSON, using fallback")
        lines = [l.strip() for l in response.split("\n") if l.strip().startswith(("Q", "q", "1", "2", "3", "4", "5"))]
        return [{"id": f"q{i+1}", "question": line.lstrip("Qq12345. "), "tone": "好奇"} for i, line in enumerate(lines)]
