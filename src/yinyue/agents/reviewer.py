import re
import logging
from collections import Counter
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

    def _detect_language(self, name: str) -> str:
        """Detect primary language of a song name."""
        cjk = 0
        latin = 0
        kana = 0
        for ch in name:
            if '一' <= ch <= '鿿' or '㐀' <= ch <= '䶿':
                cjk += 1
            elif '぀' <= ch <= 'ゟ' or '゠' <= ch <= 'ヿ':
                kana += 1
            elif ch.isascii() and ch.isalpha():
                latin += 1
        if kana > 0:
            return "日文"
        if cjk > latin:
            return "中文"
        if latin > cjk:
            return "英文/欧美"
        return "其他"

    def _build_context(
        self,
        playlist: Playlist,
        scores: list[NicheScores],
        user_answers: list[UserAnswer],
    ) -> str:
        songs = playlist.songs

        # --- Playlist-level stats ---

        # Genre composition
        genre_counter: Counter = Counter()
        for song in songs:
            for tag in song.genre_tags:
                genre_counter[tag] += 1
        genre_lines = []
        for tag, count in genre_counter.most_common(8):
            pct = count / len(songs) * 100 if songs else 0
            genre_lines.append(f"  - {tag}: {count}首 ({pct:.0f}%)")
        genre_str = "\n".join(genre_lines) if genre_lines else "  （无流派标签数据）"

        # Language composition
        lang_counter: Counter = Counter()
        for song in songs:
            lang_counter[self._detect_language(song.name)] += 1
        lang_lines = []
        for lang, count in lang_counter.most_common():
            pct = count / len(songs) * 100 if songs else 0
            lang_lines.append(f"  - {lang}: {count}首 ({pct:.0f}%)")
        lang_str = "\n".join(lang_lines)

        # Artist frequency (artists with 2+ songs)
        artist_counter: Counter = Counter()
        for song in songs:
            for artist in song.artists:
                artist_counter[artist.name] += 1
        frequent_artists = [(name, cnt) for name, cnt in artist_counter.most_common(10) if cnt >= 2]
        artist_lines = []
        for name, cnt in frequent_artists:
            artist_lines.append(f"  - {name}: {cnt}首")
        artist_str = "\n".join(artist_lines) if artist_lines else "  （无重复出现的艺人）"

        # Niche score distribution
        score_values = [s.overall_score for s in scores]
        avg_score = sum(score_values) / len(score_values) if score_values else 0
        high_niche = sum(1 for v in score_values if v >= 0.7)
        mid_niche = sum(1 for v in score_values if 0.3 <= v < 0.7)
        low_niche = sum(1 for v in score_values if v < 0.3)

        # Representative songs (top 3 niche + top 3 mainstream)
        sorted_scores = sorted(scores, key=lambda s: s.overall_score, reverse=True)

        def song_name(netease_id: int) -> str:
            for s in songs:
                if s.netease_id == netease_id:
                    artists = ", ".join(a.name for a in s.artists)
                    return f"{s.name} / {artists}"
            return f"ID:{netease_id}"

        top_niche_str = "\n".join(
            f"  {i+1}. {song_name(s.song_netease_id)} — 小众分:{s.overall_score:.4f}"
            for i, s in enumerate(sorted_scores[:3])
        )
        top_main_str = "\n".join(
            f"  {i+1}. {song_name(s.song_netease_id)} — 小众分:{s.overall_score:.4f}"
            for i, s in enumerate(reversed(sorted_scores[-3:]))
        )

        answers_str = "\n".join(
            f"  Q: {a.question}\n  A: {a.answer}" for a in user_answers
        ) if user_answers else "（用户未回答任何问题）"

        return f"""祥子様、请审判这份歌单：

（注意：以下所有歌名请保持原文，不要翻译成中文。请你评价整个歌单的构成和品味，而不是逐首点评歌曲。）

## 基本信息
- 名称：{playlist.name}
- 创建者：{playlist.owner_name}
- 歌曲数：{playlist.song_count}首
- 播放量：{playlist.play_count}
- 描述：{playlist.description or '（无）'}
- 标签：{', '.join(playlist.tags) if playlist.tags else '（无）'}

## 歌单成分分析
### 流派构成
{genre_str}

### 语种构成
{lang_str}

### 常驻艺人（出现 2 次以上）
{artist_str}

### 小众分分布
- 平均小众分：{avg_score:.2f}/1.0
- 真小众（≥0.7）：{high_niche}首
- 中间地带（0.3~0.7）：{mid_niche}首
- 大众歌（<0.3）：{low_niche}首

### 代表曲目（仅供参考，不必逐首点评）
🏆 最小众：
{top_niche_str}

🚨 最大众：
{top_main_str}

## 歌单主人的自白
{answers_str}

请从歌单整体成分出发开始你的审判——先看流派构成和语种比例，再看小众分分布，最后结合主人的自白画像。代表曲目仅作例证，不要逐首点评。歌名保持原文。"""

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
