import re
import logging
from yinyue.llm.base import LLMClient
from yinyue.prompts.reviewer import REVIEWER_PROMPT
from yinyue.api.models import Playlist, NicheScores, UserAnswer

logger = logging.getLogger(__name__)


class ReviewerAgent:
    """Generates Sakiko-style roast of a playlist."""

    def __init__(self, llm: LLMClient):
        self.llm = llm

    async def roast(
        self,
        playlist: Playlist,
        scores: list[NicheScores],
        user_answers: list[UserAnswer],
    ) -> dict:
        """Generate roast. Returns {"text": str, "score": float}."""
        user_content = self._build_context(playlist, scores, user_answers)
        response = await self.llm.chat(
            messages=[
                {"role": "system", "content": REVIEWER_PROMPT},
                {"role": "user", "content": user_content},
            ],
            temperature=0.9,
        )
        return self._parse_response(response)

    def _build_context(
        self,
        playlist: Playlist,
        scores: list[NicheScores],
        user_answers: list[UserAnswer],
    ) -> str:
        # Sort scores
        sorted_scores = sorted(scores, key=lambda s: s.overall_score, reverse=True)
        top_niche = sorted_scores[:5]
        top_mainstream = sorted_scores[-5:]

        def song_name(netease_id: int) -> str:
            for s in playlist.songs:
                if s.netease_id == netease_id:
                    artists = ", ".join(a.name for a in s.artists)
                    return f"{s.name} / {artists}"
            return f"ID:{netease_id}"

        top_niche_str = "\n".join(
            f"  {i+1}. {song_name(s.song_netease_id)} — 小众分:{s.overall_score:.4f}"
            for i, s in enumerate(top_niche)
        )
        top_main_str = "\n".join(
            f"  {i+1}. {song_name(s.song_netease_id)} — 小众分:{s.overall_score:.4f}"
            for i, s in enumerate(reversed(top_mainstream))
        )

        answers_str = "\n".join(
            f"  Q: {a.question}\n  A: {a.answer}" for a in user_answers
        ) if user_answers else "（用户未回答任何问题）"

        return f"""祥子様、请审判这份歌单：

## 基本信息
- 名称：{playlist.name}
- 创建者：{playlist.owner_name}
- 歌曲数：{playlist.song_count}首
- 播放量：{playlist.play_count}
- 描述：{playlist.description or '（无）'}
- 标签：{', '.join(playlist.tags) if playlist.tags else '（无）'}

## 小众分排行
🏆 最小众 Top 5：
{top_niche_str}

🚨 最大众 Top 5：
{top_main_str}

## 歌单主人的自白
{answers_str}

请开始你的审判。"""

    def _parse_response(self, response: str) -> dict:
        score = 5.0
        match = re.search(r"评分[：:]\s*(\d+(?:\.\d+)?)", response)
        if match:
            try:
                score = float(match.group(1))
                score = max(1.0, min(10.0, score))
            except ValueError:
                pass
        return {"text": response, "score": score}
