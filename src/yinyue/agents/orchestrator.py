import logging
from yinyue.llm.base import LLMClient
from yinyue.api.client import NetEaseClient
from yinyue.api.models import Playlist, Song, NicheScores, UserAnswer, AgentContext
from yinyue.scoring.engine import compute_all
from yinyue.agents.interviewer import InterviewerAgent
from yinyue.agents.reviewer import ReviewerAgent
from yinyue.agents.pdf_agent import PDFAgent

logger = logging.getLogger(__name__)


class Orchestrator:
    """Coordinates the full pipeline: scrape → interview → score → roast → PDF."""

    def __init__(self, llm: LLMClient, api_client: NetEaseClient):
        self.llm = llm
        self.api = api_client
        self.interviewer = InterviewerAgent(llm)
        self.reviewer = ReviewerAgent(llm)
        self.pdf_agent = PDFAgent()

    async def step1_fetch(self, url: str) -> Playlist:
        """Step 1: Scrape playlist from NetEase."""
        playlist_id = NetEaseClient.parse_playlist_url(url)
        if playlist_id is None:
            raise ValueError(f"无法解析歌单链接: {url}")
        playlist = await self.api.get_playlist(playlist_id)
        logger.info(f"Step 1 done: {playlist.name} ({playlist.song_count} songs)")
        return playlist

    async def step2_question(self, playlist: Playlist) -> list[dict]:
        """Step 2: Generate Sakiko-style questions."""
        questions = await self.interviewer.generate_questions(playlist)
        logger.info(f"Step 2 done: {len(questions)} questions generated")
        return questions

    def step3_score(self, songs: list[Song]) -> list[NicheScores]:
        """Step 3: Compute niche scores (no LLM, pure computation)."""
        scores = compute_all(songs)
        logger.info(f"Step 3 done: {len(scores)} songs scored")
        return scores

    async def step4_roast(
        self,
        playlist: Playlist,
        scores: list[NicheScores],
        user_answers: list[UserAnswer],
    ) -> dict:
        """Step 4: Generate Sakiko roast."""
        result = await self.reviewer.roast(playlist, scores, user_answers)
        logger.info(f"Step 4 done: roast score {result['score']}")
        return result

    async def step5_pdf(
        self,
        playlist: Playlist,
        scores: list[NicheScores],
        roast: dict,
        user_answers: list[UserAnswer] | None = None,
    ) -> str:
        """Step 5: Generate PDF report."""
        path = await self.pdf_agent.render(
            playlist=playlist,
            scores=scores,
            roast_text=roast["text"],
            roast_score=roast["score"],
            user_answers=user_answers or [],
        )
        logger.info(f"Step 5 done: {path}")
        return path

    async def run_full_pipeline(
        self, url: str, user_answers: list[UserAnswer] | None = None
    ) -> AgentContext:
        """Run the complete pipeline. Returns AgentContext with all results."""
        ctx = AgentContext(playlist_url=url)

        ctx.playlist = await self.step1_fetch(url)
        ctx.songs = ctx.playlist.songs
        ctx.questions = await self.step2_question(ctx.playlist)

        if user_answers:
            ctx.user_answers = user_answers

        ctx.niche_scores = self.step3_score(ctx.songs)

        roast = await self.step4_roast(ctx.playlist, ctx.niche_scores, ctx.user_answers)
        ctx.roast_text = roast["text"]
        ctx.roast_score = roast["score"]

        ctx.pdf_path = await self.step5_pdf(
            ctx.playlist, ctx.niche_scores, roast, ctx.user_answers
        )

        return ctx
