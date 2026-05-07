import os
import logging
from datetime import datetime
from fpdf import FPDF

from yinyue.api.models import Playlist, NicheScores, UserAnswer

logger = logging.getLogger(__name__)

OUTPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "outputs", "pdfs"))
FONT_DIR = os.path.join(os.path.dirname(__file__), "..", "output", "fonts")


class _SakikoPDF(FPDF):
    """FPDF subclass with page numbers and Ave Mujica footer."""

    def __init__(self, font_name: str, footer_text: str):
        super().__init__()
        self._font = font_name
        self._footer = footer_text
        self.set_auto_page_break(auto=True, margin=20)

    def footer(self):
        if self.page_no() == 1:
            return  # no footer on cover
        self.set_y(-15)
        self.set_font(self._font, "", 7)
        self.cell(0, 8, self._footer, align="C")
        self.set_font(self._font, "", 7)
        self.cell(0, 8, str(self.page_no()), align="R", new_x="LMARGIN", new_y="NEXT")


class PDFAgent:
    """Generates a PDF report from analysis results. No LLM needed."""

    async def render(
        self,
        playlist: Playlist,
        scores: list[NicheScores],
        roast_text: str,
        roast_score: float,
        user_answers: list[UserAnswer] | None = None,
    ) -> str:
        """Generate PDF and return the file path."""
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        filename = f"playlist_{playlist.netease_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        filepath = os.path.join(OUTPUT_DIR, filename)

        chinese_font = self._find_chinese_font()
        if chinese_font:
            lang = "zh"
            texts = {
                "title": "你才是真正的小众king",
                "subtitle": "歌单分析报告",
                "cover_quote": "「ようこそ、仮面の舞踏会へ」",
                "cover_line1": "—— 豊川祥子（Ave Mujica）",
                "cover_line2": "跌丝袜。",
                "info_playlist": "歌单",
                "info_creator": "创建者",
                "info_songs": "歌曲数",
                "info_plays": "播放量",
                "info_date": "分析时间",
                "niche_title": "小众排行 Top 5",
                "roast_title": f"AI 锐评  ·  {roast_score:.1f} / 10",
                "answers_title": "你的回答",
                "easter_egg": "「人は自分が見たいものしか見えない。でも、わたくしはその仮面を剥がすのが好きなの。」",
                "easter_caption": "—— 丰川祥子，于 Ave Mujica 剧场后台",
                "footer_text": "由丰川祥子（Ave Mujica）倾情审判 | 跌丝袜 | 仅供娱乐",
            }
        else:
            lang = "en"
            texts = {
                "title": "Niche King",
                "subtitle": "Playlist Analysis Report",
                "cover_quote": '"Welcome to the masked ball."',
                "cover_line1": "—— Sakiko Togawa (Ave Mujica)",
                "cover_line2": "",
                "info_playlist": "Playlist",
                "info_creator": "Creator",
                "info_songs": "Songs",
                "info_plays": "Plays",
                "info_date": "Analyzed",
                "niche_title": "Top 5 Niche Songs",
                "roast_title": f"AI Roast  ·  {roast_score:.1f} / 10",
                "answers_title": "Your Answers",
                "easter_egg": '"People see only what they want to see. But I enjoy peeling off those masks."',
                "easter_caption": "—— Sakiko Togawa, backstage at Ave Mujica",
                "footer_text": "Judged by Sakiko (Ave Mujica) | For entertainment only",
            }

        font_name = "CJK" if chinese_font else "Helvetica"
        if chinese_font:
            pdf = _SakikoPDF(font_name, f" {texts['footer_text']} ")
            pdf.add_font("CJK", "", chinese_font)
            pdf.add_font("CJK", "B", chinese_font)
        else:
            pdf = _SakikoPDF(font_name, f" {texts['footer_text']} ")

        # ── Cover page ──────────────────────────────────────
        pdf.add_page()
        pdf.ln(30)

        # Decorative border
        pdf.set_draw_color(100, 80, 140)
        pdf.set_line_width(0.6)
        margin = 18
        pdf.rect(margin, margin, pdf.w - 2 * margin, pdf.h - 2 * margin)

        pdf.ln(15)
        pdf.set_font(font_name, "B", 28)
        pdf.cell(0, 16, texts["title"], new_x="LMARGIN", new_y="NEXT", align="C")

        pdf.set_font(font_name, "", 14)
        pdf.set_text_color(120, 100, 160)
        pdf.cell(0, 12, texts["subtitle"], new_x="LMARGIN", new_y="NEXT", align="C")
        pdf.set_text_color(0, 0, 0)

        pdf.ln(15)

        # Separator line
        self._centered_line(pdf, 60, (120, 100, 160))

        pdf.ln(12)
        pdf.set_font(font_name, "", 11)
        pdf.cell(0, 10, texts["cover_quote"], new_x="LMARGIN", new_y="NEXT", align="C")

        pdf.ln(4)
        pdf.set_font(font_name, "", 10)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(0, 8, texts["cover_line1"], new_x="LMARGIN", new_y="NEXT", align="C")
        if texts["cover_line2"]:
            pdf.cell(0, 8, texts["cover_line2"], new_x="LMARGIN", new_y="NEXT", align="C")
        pdf.set_text_color(0, 0, 0)

        # ── Report page ────────────────────────────────────
        pdf.add_page()
        pdf.set_font(font_name, "B", 20)
        pdf.cell(0, 14, texts["title"], new_x="LMARGIN", new_y="NEXT", align="C")
        pdf.set_font(font_name, "", 10)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(0, 8, texts["subtitle"], new_x="LMARGIN", new_y="NEXT", align="C")
        pdf.set_text_color(0, 0, 0)
        pdf.ln(6)
        self._divider(pdf)

        # Basic info
        pdf.set_font(font_name, "B", 11)
        pdf.cell(0, 9, "基本信息", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font(font_name, "", 10)
        info = [
            (texts["info_playlist"], playlist.name),
            (texts["info_creator"], playlist.owner_name),
            (texts["info_songs"], f"{playlist.song_count} 首"),
            (texts["info_plays"], f"{playlist.play_count:,}"),
            (texts["info_date"], datetime.now().strftime("%Y-%m-%d %H:%M")),
        ]
        for label, value in info:
            pdf.set_font(font_name, "B", 10)
            pdf.cell(22, 7, f"{label}:", new_x="RIGHT", new_y="LAST")
            pdf.set_font(font_name, "", 10)
            pdf.cell(0, 7, f"  {value}", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(4)
        self._divider(pdf)

        # Niche ranking
        pdf.set_font(font_name, "B", 13)
        pdf.cell(0, 10, texts["niche_title"], new_x="LMARGIN", new_y="NEXT")
        pdf.set_font(font_name, "", 10)
        sorted_scores = sorted(scores, key=lambda s: s.overall_score, reverse=True)
        for i, s in enumerate(sorted_scores[:5]):
            name = self._song_name(playlist, s.song_netease_id)
            bar = self._score_bar(s.overall_score)
            pdf.set_font(font_name, "", 10)
            pdf.cell(8, 7, f"{i+1}.", new_x="RIGHT", new_y="LAST")
            pdf.cell(0, 7, f" {name}", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font(font_name, "", 8)
            pdf.set_text_color(100, 100, 100)
            pdf.cell(8, 5, "", new_x="RIGHT", new_y="LAST")
            pdf.cell(0, 5, f"   小众指数 {bar} {s.overall_score:.4f}", new_x="LMARGIN", new_y="NEXT")
            pdf.set_text_color(0, 0, 0)
        pdf.ln(4)
        self._divider(pdf)

        # Roast
        pdf.set_font(font_name, "B", 13)
        pdf.cell(0, 10, texts["roast_title"], new_x="LMARGIN", new_y="NEXT")
        pdf.set_font(font_name, "", 10)
        for line in roast_text.split("\n"):
            safe_line = self._safe_text(line, font_name)
            if safe_line.strip():
                pdf.multi_cell(0, 6, safe_line, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(4)
        self._divider(pdf)

        # User answers
        if user_answers:
            pdf.set_font(font_name, "B", 13)
            pdf.cell(0, 10, texts["answers_title"], new_x="LMARGIN", new_y="NEXT")
            for a in user_answers:
                pdf.set_font(font_name, "B", 10)
                pdf.multi_cell(0, 6, f"Q: {a.question}", new_x="LMARGIN", new_y="NEXT")
                pdf.set_font(font_name, "", 10)
                pdf.multi_cell(0, 6, f"A: {a.answer}", new_x="LMARGIN", new_y="NEXT")
                pdf.ln(3)
            self._divider(pdf)

        # Easter egg
        pdf.ln(6)
        pdf.set_font(font_name, "", 9)
        pdf.set_text_color(120, 100, 160)
        pdf.cell(0, 7, texts["easter_egg"], new_x="LMARGIN", new_y="NEXT", align="C")
        pdf.set_font(font_name, "", 8)
        pdf.set_text_color(150, 140, 170)
        pdf.cell(0, 6, texts["easter_caption"], new_x="LMARGIN", new_y="NEXT", align="C")
        pdf.set_text_color(0, 0, 0)

        pdf.output(filepath)
        logger.info(f"PDF saved: {filepath}")
        return filepath

    def _song_name(self, playlist: Playlist, netease_id: int) -> str:
        for s in playlist.songs:
            if s.netease_id == netease_id:
                artists = ", ".join(a.name for a in s.artists)
                return f"{s.name} / {artists}"
        return f"ID:{netease_id}"

    def _safe_text(self, text: str, font_name: str) -> str:
        if font_name == "Helvetica":
            return text.encode("latin-1", errors="replace").decode("latin-1")
        # Strip emoji glyphs that CJK fonts rarely support
        return "".join(
            ch for ch in text
            if not (0x1F000 <= ord(ch) <= 0x1FFFF or 0xFE00 <= ord(ch) <= 0xFE0F)
        )

    def _score_bar(self, score: float) -> str:
        """Mini bar chart for niche score using ASCII."""
        n = min(int(score * 10), 10)
        return "#" * n + "-" * (10 - n)

    def _divider(self, pdf: FPDF):
        """Draw a subtle horizontal divider."""
        pdf.set_draw_color(180, 175, 195)
        pdf.set_line_width(0.2)
        y = pdf.get_y() + 1
        pdf.line(pdf.l_margin, y, pdf.w - pdf.r_margin, y)
        pdf.ln(4)

    def _centered_line(self, pdf: FPDF, width_mm: float, color: tuple):
        """Draw a centered horizontal line."""
        pdf.set_draw_color(*color)
        pdf.set_line_width(0.5)
        x = (pdf.w - width_mm) / 2
        y = pdf.get_y()
        pdf.line(x, y, x + width_mm, y)

    def _find_chinese_font(self) -> str | None:
        preferred = [
            os.path.join(FONT_DIR, "NotoSansSC-Regular.ttf"),
            "C:/Windows/Fonts/simkai.ttf",
            "C:/Windows/Fonts/simsunb.ttf",
            "C:/Windows/Fonts/msyh.ttc",
            "C:/Windows/Fonts/simsun.ttc",
        ]
        fallback = [
            "C:/Windows/Fonts/NotoSansSC-VF.ttf",
        ]
        for path in preferred + fallback:
            if os.path.exists(path):
                return path
        return None
