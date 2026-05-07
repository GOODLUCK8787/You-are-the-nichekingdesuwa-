# PROJECT_CONTEXT

## 项目身份

**名称**: 你才是真正的小众king  
**类型**: 网易云歌单分析 + Agent 锐评 + PDF 输出  
**阶段**: v0.2 打磨中  
**最后更新**: 2026-05-07

---

## 核心流程（一句话）

用户粘贴网易云歌单链接 → Agent 扒数据 → 祥子反问你 3-5 个问题 → 你回答 → 小众评分 + 毒舌锐评 → PDF 报告

---

## AI 人设

**丰川祥子（Togawa Sakiko）** — 《BanG Dream! Ave Mujica》键盘手兼制作人
- 大小姐式优雅 + 毒舌 + Ave Mujica 假面/人偶/剧场美学
- 用中文阴阳怪气，不是日文翻译机
- 句尾偶尔加"跌丝袜"（ですわ）作为口癖

---

## 技术栈

| 层 | 选型 |
|---|------|
| 语言/包管理 | Python 3.12 + pip |
| 网易云数据 | **pycloudmusic**（歌单/歌曲） |
| 浏览器登录 | **Playwright**（Chromium 自动化，扫码登录方案 B） |
| LLM | DeepSeek v4-pro（支持 function calling） |
| Agent | 纯手写，OpenAI SDK function calling，不依赖 LangChain/CrewAI |
| UI | Streamlit（6 阶段状态机） |
| 存储 | SQLite（缓存歌单数据） |
| PDF | fpdf2 + simkai.ttf 中文字体 |
| 进度 | rich（终端日志） |

---

## 小众分公式

```
niche_score = 0.35 × 播放量分 + 0.25 × 渗透率分 + 0.25 × 艺人独立分 + 0.15 × 流派稀有度
```

---

## Agent 架构（5 Agent + Orchestrator）

| Agent | 职责 |
|-------|------|
| Data Agent | `step1_fetch(url)` — 扒歌单 + 歌曲详情 |
| Interviewer Agent | `step2_question(playlist)` — 根据歌单动态生成 3-5 个问题反问用户 |
| Analyst Agent | `step3_score(songs)` — 小众分计算（纯算法，不调 LLM） |
| Reviewer Agent | `step4_roast(playlist, scores, answers)` — 祥子毒舌锐评 |
| PDF Agent | `step5_pdf(playlist, scores, roast, answers)` — 生成 PDF 报告 |

---

## 登录方案

| 方式 | 实现 | 状态 |
|------|------|------|
| Cookie 登录 | 用户从浏览器复制 MUSIC_U 粘贴 | ✅ 推荐，100% 可用 |
| 浏览器扫码 | Playwright 打开 Chromium → 用户在网易官网扫码 → 自动提取 Cookie | ✅ v0.2 新增 |
| API 扫码 | ~~调用网易 QR API 自生成二维码~~ | ❌ 已废弃，反爬太严 |

---

## 文件清单

```
C:\Users\heze\yinyue\
├── pyproject.toml
├── .gitignore
├── .env.example
├── .env
├── PROJECT_CONTEXT.md
├── README.md
├── 启动.bat                              # Windows 一键启动
├── 你才是真正的小众king-项目蓝图.md
├── .streamlit/
│   └── config.toml                       # gatherUsageStats = false
├── .claude/
│   ├── settings.local.json
│   └── plans/calm-churning-emerson.md
└── src/
    └── yinyue/
        ├── __init__.py
        ├── db/
        │   ├── __init__.py
        │   ├── schema.sql
        │   └── database.py
        ├── api/
        │   ├── __init__.py
        │   ├── models.py                 # Song, Playlist, NicheScores, UserAnswer, AgentContext 等
        │   ├── pycloudmusic_adapter.py   # cookie 登录 + 浏览器登录 + 歌单/歌曲 API
        │   ├── browser_login.py          # ★ v0.2 新增：Playwright 浏览器扫码登录
        │   └── client.py                 # 统一入口 + URL 解析
        ├── llm/
        │   ├── __init__.py
        │   ├── base.py                   # LLMClient 抽象基类
        │   └── deepseek_client.py        # DeepSeek v4-pro 客户端（AsyncOpenAI）
        ├── agents/
        │   ├── __init__.py
        │   ├── base.py
        │   ├── tools.py
        │   ├── interviewer.py
        │   ├── reviewer.py               # 上下文构建 + 评分正则提取
        │   ├── pdf_agent.py
        │   └── orchestrator.py           # 5 步管线总调度
        ├── prompts/
        │   ├── __init__.py
        │   ├── orchestrator.py
        │   ├── interviewer.py
        │   └── reviewer.py               # ★ 祥子中文锐评提示词（禁止翻译歌名）
        ├── ui/
        │   ├── __init__.py
        │   ├── app.py                    # Streamlit 6 阶段 UI
        │   └── sakiko.png                # 祥子头像
        ├── scraper/
        │   ├── __init__.py
        │   ├── rate_limiter.py
        │   └── pipeline.py
        └── scoring/
            ├── __init__.py
            ├── play_count.py
            ├── playlist_penetration.py
            ├── artist_indie.py
            ├── genre_rarity.py
            └── engine.py
```

---

## v0.2 变更（2026-05-07，未提交）

### 祥子锐评中文优化
- **`prompts/reviewer.py`**: 重写提示词，强制全文中文 + 禁止翻译歌名 + 去翻译腔
  - 新增"你是用中文阴阳怪气的高手，不是把日语翻译成中文的翻译机"
  - 歌名铁律：绝对禁止翻译歌名，保持原文
- **`agents/reviewer.py`**: 上下文构建时双重强调"歌名保持原文，不要翻译"

### 扫码登录重做（Playwright 方案）
- **`api/browser_login.py`**: ★ 新文件。Playwright 启动 Chromium → 打开 music.163.com → 用户扫码 → 自动提取 Cookie
- **`api/pycloudmusic_adapter.py`**: 新增 `launch_browser_login()` + `finish_browser_login()` 方法
- **`ui/app.py`**: Tab 2 从 API 扫码改为浏览器扫码登录，移除 pycloudmusic QR 依赖

### UI 修复
- **`ui/app.py`**: 
  - `render_loading_questions()` — 必定生成问题，LLM 失败 fallback 3 个预设问题
  - `render_questions()` — 去掉跳过按钮，单提交入口
  - `render_results()` — 锐评改用 `st.markdown()` 渲染，小众排行进 expander

---

## v0.1 完成（已提交：4dde09d → f271c17）

全部 7 个 Phase 完成，42+ 个文件已提交 Git（master 分支，5 个 commit）。

### 关键修复记录
- **pycloudmusic `_login()` 无限递归**: 绕过 `_login()`，直接用 aiohttp 调 API
- **QR 状态码 8821**: 补充到状态消息映射
- **Streamlit 启动卡住**: `.streamlit/config.toml` 设 `gatherUsageStats = false`
- **fpdf2 CJK 渲染**: simkai.ttf 优先，`multi_cell` 加 `new_x="LMARGIN", new_y="NEXT"`
- **DeepSeek 模型更名**: `deepseek-chat` → `deepseek-v4-pro`
- **启动 bat 中文乱码**: 全部改为英文输出

---

## 后续可选方向（v0.3+）
- RAG 曲库推歌（BGE embeddings + ChromaDB 向量检索）
- 游客模式（不登录也能分析公开歌单）
- Streamlit Cloud 部署
- 多用户支持 / 分析历史管理
