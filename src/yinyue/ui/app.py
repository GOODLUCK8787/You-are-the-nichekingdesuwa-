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

# Load API key: Streamlit Cloud secrets > .env file > env var
try:
    _secrets_key = st.secrets.get("DEEPSEEK_API_KEY", "")
except Exception:
    _secrets_key = ""
if _secrets_key:
    os.environ["DEEPSEEK_API_KEY"] = _secrets_key
else:
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
    return asyncio.run(coro)


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

def _api_key_from_secrets() -> str | None:
    “””Check if API key is set via Streamlit secrets (cloud deployment).”””
    try:
        return st.secrets.get(“DEEPSEEK_API_KEY”, “”)
    except Exception:
        return None


def _browser_login_available() -> bool:
    “””Check if Playwright + Chromium is installed for browser-based login.”””
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
        return True
    except ImportError:
        return False


def render_login():
    st.markdown('<p class=”sakiko-title”>🎭 你才是真正的小众king</p>', unsafe_allow_html=True)
    st.markdown('<p class=”sakiko-subtitle”>豊川祥子による審判</p>', unsafe_allow_html=True)

    secrets_key = _api_key_from_secrets()
    env_key = os.getenv(“DEEPSEEK_API_KEY”)

    if not secrets_key and not env_key:
        with st.expander(“🔑 API 设置”, expanded=True):
            api_key = st.text_input(
                “DeepSeek API Key”,
                value=””,
                type=”password”,
                placeholder=”sk-...”,
                help=”在 platform.deepseek.com 注册获取”,
            )
            if api_key:
                st.session_state.api_key = api_key

        if not st.session_state.api_key:
            st.warning(“请先设置 DeepSeek API Key 再继续”)
            return
    else:
        st.session_state.api_key = secrets_key or env_key or “”
        st.success(“API Key 已配置 ✓”)
        if st.button(“🔓 清除 API Key 并退出”, key=”clear_key”):
            st.session_state.api_key = “”
            os.environ.pop(“DEEPSEEK_API_KEY”, None)
            st.rerun()

    st.divider()

    if not st.session_state.api_key:
        return

    client = get_api_client()

    st.markdown(“### 🔐 登录网易云音乐”)

    browser_ok = _browser_login_available()

    if browser_ok:
        tab1, tab2 = st.tabs([“🍪 Cookie 登录（推荐）”, “🌐 浏览器扫码登录”])
    else:
        tab1 = st.container()
        tab2 = None
        st.info(“💡 云端部署仅支持 Cookie 登录方式，浏览器扫码需本地运行”)

    # ── Tab 1: Cookie login ──────────────────────────────
    with tab1:
        st.markdown(“””
        **如何获取 Cookie：**
        1. 浏览器打开 [music.163.com](https://music.163.com) 并登录
        2. 按 `F12` → `Application`（应用程序）→ `Cookies` → `music.163.com`
        3. 找到 `MUSIC_U`，复制它的值
        4. 粘贴到下方输入框
        “””)
        cookie_input = st.text_input(
            “MUSIC_U Cookie”,
            placeholder=”粘贴 MUSIC_U 的值或完整 Cookie 字符串...”,
            label_visibility=”collapsed”,
        )
        if cookie_input and st.button(“🚀 登录”, key=”cookie_login”, use_container_width=True):
            if client.login_with_cookie(cookie_input):
                st.session_state.phase = “input”
                st.rerun()
            else:
                st.error(“Cookie 无效，请检查是否已登录 music.163.com 并正确复制了 MUSIC_U 的值”)

    # ── Tab 2: Browser QR login ────────────────────────────
    if tab2:
        with tab2:
            st.markdown(“””
            **流程：**
            1. 点击下方按钮 → 弹出网易云官网登录窗口
            2. 在窗口中用手机扫码登录
            3. 登录成功后回到本页面，点击”检查登录状态”
            “””)

            if “browser_launched” not in st.session_state:
                st.session_state.browser_launched = False

            status_placeholder = st.empty()

            if not st.session_state.browser_launched:
                if st.button(“🌐 打开网易云登录窗口”, use_container_width=True, type=”primary”):
                    proc = client._adapter.launch_browser_login()
                    if proc is None:
                        st.error(“未安装 Playwright，请先运行：pip install playwright && playwright install chromium”)
                    else:
                        st.session_state.browser_launched = True
                        st.rerun()
            else:
                status_placeholder.info(“浏览器窗口已打开，请在窗口中用手机扫码登录网易云...”)

                col1, col2 = st.columns(2)
                with col1:
                    if st.button(“✅ 检查登录状态”, use_container_width=True):
                        if client._adapter.finish_browser_login():
                            status_placeholder.success(“登录成功！”)
                            st.session_state.phase = “input”
                            st.session_state.browser_launched = False
                            st.rerun()
                        else:
                            status_placeholder.warning(“还在等待登录，请在浏览器窗口里先扫码”)
                with col2:
                    if st.button(“🔄 重新打开”, use_container_width=True):
                        st.session_state.browser_launched = False
                        st.rerun()

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
    """Generate questions from LLM, then jump to questions phase."""
    orch = get_orchestrator()
    playlist = st.session_state.playlist

    st.markdown(f"### 📋 {playlist.name}")
    st.caption(f"By {playlist.owner_name} · {playlist.song_count} 首歌 · {playlist.play_count} 次播放")

    # Always generate questions — LLM first, fallback if it fails
    with st.spinner("祥子正在审视你的歌单，想想怎么拷问你..."):
        try:
            questions = _run(orch.interviewer.generate_questions(playlist))
            if not questions or len(questions) == 0:
                raise ValueError("LLM returned empty questions")
            st.session_state.questions = questions
        except Exception as e:
            st.session_state.questions = FALLBACK_QUESTIONS

    st.session_state.phase = "questions"
    st.rerun()


# ── Phase: Questions ─────────────────────────────────────────

def render_questions():
    playlist = st.session_state.playlist
    questions = st.session_state.questions
    user_answers = st.session_state.user_answers

    st.markdown(f"### 🎤 祥子有 {len(questions)} 个问题想问贵方")
    st.caption(f"关于「{playlist.name}」——")

    tone_caption = {
        "好奇": "祥子微微倾头",
        "审视": "祥子推了推眼镜",
        "挑衅": "祥子嘴角上扬",
        "感叹": "祥子轻叹一声",
    }

    for q in questions:
        qid = q["id"]
        tone = q.get("tone", "")
        st.markdown(f"**{q['question']}**")
        if tone in tone_caption:
            st.caption(tone_caption[tone])
        answer = st.text_input(
            "你的回答",
            key=f"answer_{qid}",
            placeholder="说点什么吧，沉默也是一种回答...",
            label_visibility="collapsed",
        )
        if answer:
            user_answers[qid] = answer
        st.divider()

    answered_count = sum(1 for q in questions if user_answers.get(q["id"]))
    st.caption(f"已回答 {answered_count}/{len(questions)} 题")

    if st.button("⚡ 提交，接受审判", type="primary", use_container_width=True):
        _build_answers(questions, user_answers, fill_empty=True)
        st.session_state.phase = "analyzing"
        st.rerun()


def _build_answers(questions, user_answers, fill_empty=False):
    st.session_state.user_answers_data = [
        UserAnswer(
            question_id=q["id"],
            question=q["question"],
            answer=user_answers.get(q["id"]) or "（未回答）",
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

    sorted_scores = sorted(scores, key=lambda s: s.overall_score, reverse=True)

    # ── Score header ──────────────────────────────────────
    col_a, col_b = st.columns([1, 2])
    with col_a:
        st.markdown(f'<p class="score-badge">{roast["score"]:.1f} / 10</p>', unsafe_allow_html=True)
        st.caption("綜合評分")
    with col_b:
        top_niche = sorted_scores[0] if sorted_scores else None
        if top_niche:
            top_name = _song_name(playlist, top_niche.song_netease_id)
            st.metric("最小眾單曲", top_name, f"{top_niche.overall_score:.3f}")

    st.divider()

    # ── Roast (rendered as proper markdown) ───────────────
    st.markdown("### 📝 祥子的銳評")
    # Clean up the roast text for markdown rendering
    roast_md = roast["text"]
    # Remove leading/trailing whitespace
    roast_md = roast_md.strip()
    with st.container(border=True):
        st.markdown(roast_md)

    # ── Niche ranking ─────────────────────────────────────
    with st.expander("🏆 查看小众排行 Top 5"):
        for i, s in enumerate(sorted_scores[:5]):
            name = _song_name(playlist, s.song_netease_id)
            score_pct = int(s.overall_score * 100)
            st.markdown(f"{i+1}. **{name}**")
            bar = "▰" * (score_pct // 10) + "▱" * (10 - score_pct // 10)
            st.caption(f"小众指数  {bar}  {s.overall_score:.4f}")

    # ── PDF download ──────────────────────────────────────
    st.divider()
    if pdf_path and os.path.exists(pdf_path):
        with open(pdf_path, "rb") as f:
            st.download_button(
                label="📥 下载 PDF 报告",
                data=f,
                file_name=os.path.basename(pdf_path),
                mime="application/pdf",
                use_container_width=True,
            )
    else:
        st.warning("PDF 文件不存在，請重試")

    # ── Actions ───────────────────────────────────────────
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
