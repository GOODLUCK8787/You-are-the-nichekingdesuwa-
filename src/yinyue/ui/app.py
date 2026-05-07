"""
你才是真正的小众king — Streamlit Web UI
Sakiko Togawa (Ave Mujica) playlist analysis app.
"""
import asyncio
import logging
import os
import sys
from io import BytesIO
from pathlib import Path

import qrcode
import streamlit as st
from dotenv import load_dotenv

# Ensure project root is on path
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(_PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT / "src"))

from yinyue.api.client import NetEaseClient
from yinyue.llm.deepseek_client import DeepSeekClient
from yinyue.agents.orchestrator import Orchestrator
from yinyue.api.models import UserAnswer

load_dotenv(_PROJECT_ROOT / ".env")
logger = logging.getLogger(__name__)

# ── Page config (must be first st call) ──────────────────────
st.set_page_config(
    page_title="你才是真正的小众king",
    page_icon="🎭",
    layout="centered",
)

# ── CSS ──────────────────────────────────────────────────────
st.markdown("""
<style>
    .sakiko-title { font-size: 2.2rem; font-weight: 700; text-align: center; margin-bottom: 0; }
    .sakiko-subtitle { font-size: 1rem; color: #888; text-align: center; margin-bottom: 2rem; }
    .sakiko-quote { font-style: italic; color: #b8a0d0; text-align: center; font-size: 0.9rem; }
    .roast-box { background: #1a1a2e; border: 1px solid #5a4a7a; border-radius: 10px; padding: 1.2rem; margin: 1rem 0; white-space: pre-wrap; font-size: 0.95rem; line-height: 1.7; }
    .score-badge { font-size: 2rem; font-weight: 700; color: #c4a0e0; text-align: center; }
    .niche-rank { font-family: monospace; font-size: 0.9rem; }
</style>
""", unsafe_allow_html=True)


# ── Async helper ─────────────────────────────────────────────

def _run(coro):
    """Run an async coroutine from Streamlit's sync context."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    # Rare: already inside a running loop — create a new one in a thread
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(lambda c: asyncio.run(c), coro).result()


# ── Session helpers ──────────────────────────────────────────

def init_session():
    defaults = {
        "phase": "login",
        "api_client": None,
        "orchestrator": None,
        "qr_key": None,
        "qr_url": None,
        "playlist": None,
        "questions": [],
        "user_answers": {},
        "scores": [],
        "roast": None,
        "pdf_path": None,
        "error": None,
        "api_key": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def get_api_client():
    if st.session_state.api_client is None:
        st.session_state.api_client = NetEaseClient(rate=3.0)
    return st.session_state.api_client


def get_orchestrator():
    if st.session_state.orchestrator is None:
        api_key = st.session_state.api_key or os.getenv("DEEPSEEK_API_KEY", "")
        if not api_key:
            return None
        llm = DeepSeekClient(api_key=api_key)
        api = get_api_client()
        st.session_state.orchestrator = Orchestrator(llm=llm, api_client=api)
    return st.session_state.orchestrator


def generate_qr_image(url: str) -> BytesIO:
    qr = qrcode.QRCode(border=2, box_size=10)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#1a1a2e", back_color="#f0e8ff")
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


def _song_name(playlist, netease_id: int) -> str:
    for s in playlist.songs:
        if s.netease_id == netease_id:
            artists = ", ".join(a.name for a in s.artists)
            return f"{s.name} / {artists}"
    return f"ID:{netease_id}"


def _reset_analysis():
    """Clear analysis state, keep login."""
    for key in [
        "phase", "qr_key", "qr_url", "playlist", "questions",
        "user_answers", "user_answers_data", "scores", "roast", "pdf_path", "error",
    ]:
        if key in st.session_state:
            del st.session_state[key]
    st.session_state.phase = "input"


FALLBACK_QUESTIONS = [
    {"id": "q1", "question": "这张歌单里，哪首歌对你来说有特别的意义？", "tone": "好奇"},
    {"id": "q2", "question": "你是从什么时候开始听这类音乐的？", "tone": "审视"},
    {"id": "q3", "question": "如果有人批评你的音乐品味，你会怎么回应？", "tone": "挑衅"},
]


# ── Phase: Login ─────────────────────────────────────────────

def render_login():
    st.markdown('<p class="sakiko-title">🎭 你才是真正的小众king</p>', unsafe_allow_html=True)
    st.markdown('<p class="sakiko-subtitle">豊川祥子による審判</p>', unsafe_allow_html=True)

    with st.expander("🔑 API 设置", expanded=not os.getenv("DEEPSEEK_API_KEY")):
        api_key = st.text_input(
            "DeepSeek API Key",
            value=os.getenv("DEEPSEEK_API_KEY", ""),
            type="password",
            placeholder="sk-...",
            help="在 platform.deepseek.com 注册获取",
        )
        if api_key:
            st.session_state.api_key = api_key

    st.divider()

    if not st.session_state.api_key and not os.getenv("DEEPSEEK_API_KEY"):
        st.warning("请先设置 DeepSeek API Key 再继续")
        return

    client = get_api_client()

    if st.session_state.qr_key is None:
        with st.spinner("正在生成登录二维码..."):
            try:
                qr_data = _run(client.get_qr())
                st.session_state.qr_key = qr_data["key"]
                st.session_state.qr_url = qr_data["url"]
            except Exception as e:
                st.error(f"获取二维码失败，请检查网络连接: {e}")
                return

    qr_img = generate_qr_image(st.session_state.qr_url)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.image(qr_img, caption="📱 请使用网易云音乐 App 扫描二维码", use_container_width=True)

    st.markdown('<p class="sakiko-quote">「わたくしの審判を受ける覚悟はあって？」</p>', unsafe_allow_html=True)

    col_a, col_b, col_c = st.columns([1, 1, 1])
    with col_b:
        if st.button("🔍 检查登录状态", use_container_width=True):
            with st.spinner("确认中..."):
                try:
                    result = _run(client.check_qr(st.session_state.qr_key))
                    status = result["status"]
                    if status == 803:
                        st.session_state.phase = "input"
                        st.rerun()
                    elif status == 802:
                        st.info("已扫码，请在手机上点击确认登录")
                    elif status == 801:
                        st.info("等待扫码中...")
                    elif status == 800:
                        st.warning("二维码已过期")
                        st.session_state.qr_key = None
                        st.rerun()
                except Exception as e:
                    st.error(f"检查登录失败: {e}")

    col_x, col_y, col_z = st.columns([1, 1, 1])
    with col_y:
        if st.button("🔄 刷新二维码", use_container_width=True):
            st.session_state.qr_key = None
            st.session_state.qr_url = None
            st.rerun()

    st.caption("提示：请先在手机网易云 App 中扫码并确认，再点击上方按钮检查。")


# ── Phase: URL Input ─────────────────────────────────────────

def render_input():
    st.markdown('<p class="sakiko-title">🎭 你才是真正的小众king</p>', unsafe_allow_html=True)

    orch = get_orchestrator()
    if orch is None:
        st.error("Orchestrator 初始化失败，请检查 API Key")
        return

    st.markdown("### いらっしゃい、贵方の歌单を見せなさい")
    st.caption("粘贴网易云歌单链接，让我看看你的品味究竟有几分斤两。")

    url = st.text_input(
        "歌单链接",
        placeholder="https://music.163.com/playlist?id=xxxxxx",
        label_visibility="collapsed",
    )

    if url:
        playlist_id = NetEaseClient.parse_playlist_url(url)
        if playlist_id is None:
            st.error("无法识别该链接，请确认是网易云歌单链接（包含 playlist?id=... ）")
            return

        with st.spinner("祥子正在翻阅你的歌单..."):
            try:
                playlist = _run(orch.step1_fetch(url))
                st.session_state.playlist = playlist
                st.session_state.phase = "loading_questions"
                st.rerun()
            except Exception as e:
                st.error(f"获取歌单失败: {e}")


# ── Phase: Generating questions ──────────────────────────────

def render_loading_questions():
    orch = get_orchestrator()
    playlist = st.session_state.playlist

    st.markdown(f"### 📋 {playlist.name}")
    st.caption(f"By {playlist.owner_name} · {playlist.song_count} 首歌 · {playlist.play_count} 次播放")

    with st.spinner("祥子正在审视你的歌单，思考要问什么..."):
        try:
            questions = _run(orch.interviewer.generate_questions(playlist))
            st.session_state.questions = questions
        except Exception as e:
            st.warning(f"LLM 生成问题失败，使用默认问题: {e}")
            st.session_state.questions = FALLBACK_QUESTIONS

    st.session_state.phase = "questions"
    st.rerun()


# ── Phase: Questions ─────────────────────────────────────────

def render_questions():
    st.markdown("### 🎤 先回答我几个问题")

    questions = st.session_state.questions
    user_answers = st.session_state.user_answers

    tone_caption = {
        "好奇": "祥子微微倾头",
        "审视": "祥子推了推眼镜",
        "挑衅": "祥子嘴角上扬",
        "感叹": "祥子轻叹一声",
    }

    for q in questions:
        qid = q["id"]
        st.markdown(f"**{q['question']}**")
        st.caption(tone_caption.get(q.get("tone", ""), ""))
        answer = st.text_input(
            "你的回答",
            key=f"answer_{qid}",
            placeholder="输入你的回答...",
            label_visibility="collapsed",
        )
        if answer:
            user_answers[qid] = answer
        st.divider()

    col1, col2 = st.columns(2)
    answered_count = len([q for q in questions if user_answers.get(q["id"])])

    if answered_count >= len(questions):
        st.success(f"已回答全部 {len(questions)} 个问题")
        with col1:
            if st.button("⚡ 提交审判", type="primary", use_container_width=True):
                _build_answers(questions, user_answers)
                st.session_state.phase = "analyzing"
                st.rerun()
    else:
        st.caption(f"已答 {answered_count}/{len(questions)} 题")
        with col1:
            if st.button("⚡ 提交审判", type="primary", use_container_width=True):
                _build_answers(questions, user_answers)
                st.session_state.phase = "analyzing"
                st.rerun()
    with col2:
        if st.button("跳过，直接审判", use_container_width=True):
            _build_answers(questions, user_answers, fill_empty=True)
            st.session_state.phase = "analyzing"
            st.rerun()


def _build_answers(questions, user_answers, fill_empty=False):
    st.session_state.user_answers_data = [
        UserAnswer(
            question_id=q["id"],
            question=q["question"],
            answer=user_answers.get(q["id"], "") if not fill_empty else (user_answers.get(q["id"]) or "（未回答）"),
        )
        for q in questions
    ]


# ── Phase: Analyzing ─────────────────────────────────────────

def render_analyzing():
    st.markdown("### ⚖️ 審判中...")

    orch = get_orchestrator()
    playlist = st.session_state.playlist
    user_answers = st.session_state.user_answers_data

    progress = st.progress(0, "計算小眾分...")

    try:
        progress.progress(20, "量化你的品味...")
        scores = orch.step3_score(playlist.songs)
        st.session_state.scores = scores

        progress.progress(50, "祥子正在酝酿毒舌...")
        roast = _run(orch.step4_roast(playlist, scores, user_answers))

        progress.progress(80, "撰写 PDF 报告...")
        pdf_path = _run(orch.step5_pdf(playlist, scores, roast, user_answers))

        st.session_state.roast = roast
        st.session_state.pdf_path = pdf_path
        progress.progress(100, "審判完了！")
        st.session_state.phase = "results"
        st.rerun()

    except Exception as e:
        progress.empty()
        st.error(f"分析过程出错: {e}")
        st.session_state.error = str(e)
        if st.button("🔙 返回重试"):
            st.session_state.phase = "input"
            st.rerun()


# ── Phase: Results ───────────────────────────────────────────

def render_results():
    st.markdown("### 🎭 審判結果")

    playlist = st.session_state.playlist
    scores = st.session_state.scores
    roast = st.session_state.roast
    pdf_path = st.session_state.pdf_path

    # Score overview
    sorted_scores = sorted(scores, key=lambda s: s.overall_score, reverse=True)
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown(f'<p class="score-badge">{roast["score"]:.1f} / 10</p>', unsafe_allow_html=True)
        st.caption("綜合評分")
    with col_b:
        top_niche = sorted_scores[0] if sorted_scores else None
        if top_niche:
            top_name = _song_name(playlist, top_niche.song_netease_id)
            st.metric("最小眾單曲", top_name, f"{top_niche.overall_score:.3f}")

    # Niche ranking
    st.markdown("#### 🏆 小眾排行 Top 5")
    for i, s in enumerate(sorted_scores[:5]):
        name = _song_name(playlist, s.song_netease_id)
        st.markdown(
            f'<span class="niche-rank">{i+1}. {name} — {s.overall_score:.4f}</span>',
            unsafe_allow_html=True,
        )

    # Roast text
    st.markdown("#### 📝 祥子的銳評")
    st.markdown(f'<div class="roast-box">{roast["text"]}</div>', unsafe_allow_html=True)

    # PDF download
    st.divider()
    st.markdown("#### 📥 下載報告")
    if pdf_path and os.path.exists(pdf_path):
        with open(pdf_path, "rb") as f:
            st.download_button(
                label="下載 PDF 報告",
                data=f,
                file_name=os.path.basename(pdf_path),
                mime="application/pdf",
                use_container_width=True,
            )
    else:
        st.warning("PDF 文件不存在，請重試")

    # Actions
    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 再分析一個歌單", use_container_width=True):
            _reset_analysis()
            st.rerun()
    with col2:
        if st.button("🚪 退出登錄", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()


# ── Sidebar ──────────────────────────────────────────────────

def render_sidebar():
    with st.sidebar:
        # Avatar
        avatar_path = Path(__file__).parent / "sakiko.png"
        if avatar_path.exists():
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                st.image(str(avatar_path), use_container_width=True)
        st.markdown("### 🎭 Ave Mujica")
        st.markdown("*「ようこそ、仮面の舞踏会へ」*")
        st.divider()
        phase_labels = {
            "login": "🔐 登錄",
            "input": "🔗 輸入歌單",
            "loading_questions": "🤔 祥子思考中",
            "questions": "💬 回答問題",
            "analyzing": "⚖️ 審判中",
            "results": "📋 結果",
        }
        st.caption(f"當前階段: {phase_labels.get(st.session_state.phase, st.session_state.phase)}")
        if st.session_state.playlist:
            st.caption(f"歌單: {st.session_state.playlist.name}")
        st.divider()
        st.caption("Powered by DeepSeek v3 + Streamlit")
        st.caption("人格：豊川祥子 (Ave Mujica)")
        st.caption("© 2026 你才是真正的小眾king")


# ── Main ─────────────────────────────────────────────────────

def main():
    init_session()
    render_sidebar()

    phase = st.session_state.phase
    if phase == "login":
        render_login()
    elif phase == "input":
        render_input()
    elif phase == "loading_questions":
        render_loading_questions()
    elif phase == "questions":
        render_questions()
    elif phase == "analyzing":
        render_analyzing()
    elif phase == "results":
        render_results()
    else:
        st.error(f"未知階段: {phase}")
        if st.button("🔙 返回首頁"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()


if __name__ == "__main__":
    main()
