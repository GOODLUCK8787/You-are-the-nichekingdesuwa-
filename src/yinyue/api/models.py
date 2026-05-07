from pydantic import BaseModel, Field
from typing import Optional


class Artist(BaseModel):
    netease_id: int
    name: str


class Song(BaseModel):
    netease_id: int
    name: str
    artists: list[Artist]
    album_name: Optional[str] = None
    album_id: Optional[int] = None
    duration_ms: Optional[int] = None
    play_count: int = 0
    popularity: float = Field(default=0.0, ge=0.0, le=100.0)
    genre_tags: list[str] = []


class Playlist(BaseModel):
    netease_id: int
    name: str
    description: Optional[str] = None
    owner_name: str
    owner_id: Optional[int] = None
    song_count: int
    play_count: int = 0
    share_count: int = 0
    comment_count: int = 0
    tags: list[str] = []
    create_time: Optional[int] = None
    update_time: Optional[int] = None
    url: str
    songs: list[Song] = []


class NicheScores(BaseModel):
    song_netease_id: int
    overall_score: float = Field(ge=0.0, le=1.0)
    play_count_score: float = Field(ge=0.0, le=1.0)
    penetration_score: float = Field(ge=0.0, le=1.0)
    artist_indie_score: float = Field(ge=0.0, le=1.0)
    genre_rarity_score: float = Field(ge=0.0, le=1.0)
    percentile_rank: Optional[float] = None


class UserAnswer(BaseModel):
    question_id: str
    question: str
    answer: str


class AgentContext(BaseModel):
    """Context object passed between Agents in the pipeline."""
    playlist_url: str = ""
    playlist: Optional[Playlist] = None
    songs: list[Song] = []
    questions: list[dict] = []
    user_answers: list[UserAnswer] = []
    niche_scores: list[NicheScores] = []
    roast_text: str = ""
    roast_score: float = 0.0
    pdf_path: str = ""
