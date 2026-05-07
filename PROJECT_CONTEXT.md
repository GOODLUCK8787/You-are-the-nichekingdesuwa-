# PROJECT_CONTEXT

## 项目身份

**名称**: 你才是真正的小众king  
**类型**: 网易云歌单分析 + Agent 锐评 + PDF 输出  
**阶段**: Phase 6 ✅ 完成 → Phase 7 待开始  
**最后更新**: 2026-05-07

---

## 核心流程（一句话）

用户粘贴网易云歌单链接 → Agent 扒数据 → 祥子反问你 3-5 个问题 → 你回答 → 小众评分 + 毒舌锐评 → PDF 报告

---

## AI 人设

**丰川祥子（Togawa Sakiko）** — 《BanG Dream! Ave Mujica》键盘手兼制作人
- 大小姐式优雅 + 毒舌 + Ave Mujica 假面/人偶/剧场美学
- 详见蓝图文档的 "🎭 AI 人设" 章节

---

## 技术栈

| 层 | 选型 |
|---|------|
| 语言/包管理 | Python 3.12 + pip（uv 待配 PATH） |
| 网易云数据 | **pycloudmusic**（PyPI 可用，替代了原计划的 pyncm） |
| LLM | DeepSeek v3（支持 function calling） |
| Agent | 纯手写，OpenAI SDK function calling，不依赖 LangChain/CrewAI |
| UI | Streamlit（聊天式交互） |
| 存储 | SQLite（缓存歌单数据） |
| PDF | fpdf2 + Noto Sans SC 字体 |
| 进度 | rich（终端日志） |

---

## 小众分公式

```
niche_score = 0.35 × 播放量分 + 0.25 × 渗透率分 + 0.25 × 艺人独立分 + 0.15 × 流派稀有度
```

无评论维度（评论采集太慢，已砍掉）。详见蓝图。

---

## Agent 架构（5 Agent + Orchestrator）

| Agent | 工具 | 职责 |
|-------|------|------|
| Data Agent | `fetch_playlist(url)` | 扒歌单 + 歌曲详情 |
| Interviewer Agent | `ask_user(questions)` | 根据歌单动态生成 3-5 个问题反问用户 |
| Analyst Agent | `compute_scores(songs)` | 小众分 + 风格画像 |
| Reviewer Agent | `generate_roast(context)` | 祥子毒舌锐评 |
| PDF Agent | `render_pdf(context)` | 生成 PDF 报告 |

Orchestrator 用 Context 对象在 Agent 间传递数据，逐步累积信息。

---

## 目前文件清单

```
C:\Users\heze\yinyue\
├── pyproject.toml                       # ✅ 项目配置（10 个依赖）
├── .gitignore                           # ✅ 
├── .env.example                         # ✅ DEEPSEEK_API_KEY=sk-xxx
├── PROJECT_CONTEXT.md                   # ✅ 本文件
├── 你才是真正的小众king-项目蓝图.md       # 完整项目蓝图（非技术向）
├── .claude/
│   ├── settings.local.json
│   └── plans/calm-churning-emerson.md   # 实施计划（技术向）
└── src/
    └── yinyue/
        ├── __init__.py                  # ✅ 包初始化
        ├── db/
        │   ├── __init__.py              # ✅
        │   ├── schema.sql               # ✅ 4 张表 DDL
        │   └── database.py              # ✅ init_db() + get_db()
        ├── api/
        │   ├── __init__.py              # ✅
        │   ├── models.py                # ✅ Song, Playlist, NicheScores, AgentContext 等 6 个模型
        │   ├── pycloudmusic_adapter.py  # ✅ pycloudmusic 封装（扫码登录、歌单、歌曲）
        │   └── client.py                # ✅ 统一入口 + URL 解析
        ├── llm/
        │   ├── __init__.py              # ✅
        │   ├── base.py                  # ✅ LLMClient 抽象基类（chat + chat_with_tools）
        │   └── deepseek_client.py       # ✅ DeepSeek v3 客户端（AsyncOpenAI）
        ├── agents/
        │   ├── __init__.py              # ✅
        │   ├── base.py                  # ✅ AgentBase（工具注册 + tool-use loop）
        │   ├── tools.py                 # ✅ 5 个工具定义（fetch_playlist, ask_user, compute_scores, generate_roast, render_pdf）
        │   ├── interviewer.py           # ✅ 祥子反向提问（generate_questions）
        │   ├── reviewer.py              # ✅ 祥子锐评（roast）
        │   ├── pdf_agent.py             # ✅ PDF 生成（fpdf2 + CJK 字体 + 中英双语 fallback）
        │   └── orchestrator.py          # ✅ 总调度（run_full_pipeline）
        ├── prompts/
        │   ├── __init__.py              # ✅
        │   ├── orchestrator.py          # ✅ 祥子人设 System Prompt
        │   ├── interviewer.py           # ✅ 提问风格 Prompt
        │   └── reviewer.py              # ✅ 锐评格式 Prompt
        └── ui/
            ├── __init__.py              # ✅
            └── app.py                   # ✅ Streamlit 聊天式 Web UI（6 阶段状态机）
        └── scraper/
            ├── __init__.py              # ✅
            ├── rate_limiter.py          # ✅ 令牌桶限流器（3 req/s + jitter）
            └── pipeline.py              # ✅ 采集管线（拉歌单 → 存 SQLite）
        └── scoring/
            ├── __init__.py              # ✅
            ├── play_count.py            # ✅ 播放量评分（对数归一化）
            ├── playlist_penetration.py  # ✅ 热度渗透评分
            ├── artist_indie.py          # ✅ 艺人独立评分
            ├── genre_rarity.py          # ✅ 流派稀有度查表
            └── engine.py                # ✅ 加权汇总 + 百分位排名
```

---

## 今日变更（2026-05-07）

### 今日完成

| Phase | 文件 | 验证 |
|-------|------|------|
| 1 | `pyproject.toml` + `.gitignore` + `.env.example` | `pip install -e .` ✅ |
| 1 | `src/yinyue/__init__.py` | `import yinyue` ✅ |
| 1 | `src/db/schema.sql` + `database.py` | `init_db()` → 4 张表 ✅ |
| 1 | `src/api/models.py` | 6 个 Pydantic 模型 ✅ |
| 1 | `src/llm/base.py` | `LLMClient` 抽象类 ✅ |
| 1 | `src/agents/base.py` | `AgentBase` + tool-use loop ✅ |
| 2 | `src/scraper/rate_limiter.py` | 5 req/0.84s ≈ 5 req/s ✅ |
| 2 | `src/api/pycloudmusic_adapter.py` | import + 实例化 ✅ |
| 2 | `src/api/client.py` | URL 解析 4/4 ✅ |
| 3 | `src/db/database.py` (CRUD) | save_playlist / save_song / playlist_exists ✅ |
| 3 | `src/scraper/pipeline.py` | URL 解析 + 缓存检查 + 异常处理 ✅ |
| 4 | `src/scoring/*` (6 files) | 4 子评分器 + 加权引擎; 小众 0.64 > 主流 0.01 ✅ |
| 5 | `src/llm/deepseek_client.py` | AsyncOpenAI + DeepSeek v3, chat / chat_with_tools ✅ |
| 5 | `src/agents/tools.py` | 5 个工具，OpenAI function calling 格式 ✅ |
| 5 | `src/agents/interviewer.py` | 祥子提问，JSON 解析 + 回退 ✅ |
| 5 | `src/agents/reviewer.py` | 祥子锐评，评分正则提取 ✅ |
| 5 | `src/agents/pdf_agent.py` | fpdf2 + CJK 字体（simkai.ttf），中英 fallback ✅ |
| 5 | `src/agents/orchestrator.py` | 5 步管线（fetch→question→score→roast→pdf）✅ |
| 5 | `src/prompts/*` (4 files) | 祥子人设注入到 orchestrator/interviewer/reviewer ✅ |
| 6 | `src/yinyue/ui/app.py` | Streamlit 6 阶段 UI（login→input→questions→analyze→results）✅ |
| 6 | `src/yinyue/ui/__init__.py` | 包初始化 ✅ |
| — | `pyproject.toml` | 新增 qrcode, Pillow 依赖 ✅ |
| — | `src/api/pycloudmusic_adapter.py` | 修复 QR 登录 API 调用（qr_key/qr_check/Music163BadCode）✅ |

### 数据库

- SQLite：`data/db/yinyue.db`，4 张表，`init_db()` 已验证

### 依赖

- **pycloudmusic** 替代 pyncm（pyncm 不在 PyPI 上），8/8 包验证通过

---

## 当前进度

- [x] 蓝图确认
- [x] 技术栈确定
- [x] Agent 架构设计
- [x] Phase 1 全部完成（9/9 文件）
- [x] Phase 2 全部完成（3/3 文件）
- [x] Phase 3 全部完成（pipeline + CRUD）
- [x] Phase 4 全部完成（6 个评分文件）
- [x] Phase 5: Agent 实现（★ 12 个文件全部完成）
- [x] Phase 6: Streamlit 聊天式 Web UI（★ 修复 QR 登录 + 6 阶段状态机）

---

## 下一步：Phase 7 — PDF 输出打磨 + 收尾

1. PDF 报告排版优化（封面页、图表、彩蛋）
2. 错误处理完善（网络超时、LLM 限流、缓存降级）
3. 端到端测试：扫码 → 贴链接 → 回答 → 下载 PDF
4. README.md 撰写（安装、配置、运行说明）
5. Git 初始化 + 首次提交
6. 部署准备（可选：Streamlit Cloud / 局域网分享）
