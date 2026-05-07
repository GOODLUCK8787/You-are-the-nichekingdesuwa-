# 🎭 你才是真正的小众king

> 「ようこそ、仮面の舞踏会へ」—— 丰川祥子（Ave Mujica）

粘贴网易云歌单链接，AI 丰川祥子会扒取你的歌单数据、反问你的听歌品味、计算小众指数，最后生成一份毒舌锐评 PDF 报告。

## 功能

- **一键扒歌单** — 粘贴链接，自动获取全部歌曲、播放量、艺人信息
- **AI 反向提问** — 祥子读完歌单后动态生成 3-5 个问题，句句戳痛点
- **四维小众评分** — 播放量、平台热度、艺人冷门度、流派稀有度加权计算
- **毒舌 PDF 报告** — 祥子大小姐锐评 + 人设画像 + 小众排行，输出精美 PDF
- **跌丝袜** — 祥子的经典口癖，已注入所有提示词

## 技术栈

| 层 | 选型 |
|---|------|
| UI | Streamlit（聊天式交互） |
| LLM | DeepSeek v3（OpenAI SDK function calling） |
| Agent | 纯手写，5 Agent + Orchestrator |
| 数据 | pycloudmusic（网易云 API） |
| 评分 | 对数归一化 + 加权引擎 |
| PDF | fpdf2 + 系统 CJK 字体 |
| 存储 | SQLite（歌单缓存） |

## 前置条件

- Python 3.12+
- [DeepSeek API Key](https://platform.deepseek.com)（LLM 调用）
- 网易云音乐 App（扫码登录）

## 安装

```bash
git clone <repo-url>
cd yinyue
pip install -e .
```

## 配置

```bash
cp .env.example .env
# 编辑 .env，填入你的 DeepSeek API Key
```

`.env` 内容：
```
DEEPSEEK_API_KEY=sk-xxx
```

也可以在 Web UI 侧边栏直接输入 API Key。

## 运行

```bash
streamlit run src/yinyue/ui/app.py
# 或
python -m streamlit run src/yinyue/ui/app.py
```

打开浏览器访问 `http://localhost:8501`。

## 使用流程

1. **设置 API Key** — 展开页面顶部的设置面板，输入 DeepSeek API Key
2. **扫码登录** — 用网易云 App 扫描二维码，点击"检查登录状态"
3. **粘贴歌单链接** — 粘贴任意网易云歌单链接，祥子开始扒数据
4. **回答祥子的问题** — 祥子会根据歌单内容反向提问，句句审视你的品味
5. **获取 PDF 报告** — 小众评分 + 毒舌锐评 + 人设画像，一键下载 PDF

## 项目结构

```
yinyue/
├── src/yinyue/
│   ├── api/           # 网易云 API 封装 + 数据模型
│   ├── llm/           # LLM 抽象层 + DeepSeek 客户端
│   ├── agents/        # 5 个 Agent + Orchestrator 总调度
│   ├── scoring/       # 小众评分引擎（4 维加权）
│   ├── prompts/       # 祥子人设 System Prompts
│   ├── scraper/       # 限流器 + 采集管线
│   ├── db/            # SQLite 缓存
│   └── ui/            # Streamlit Web UI
├── outputs/pdfs/      # PDF 输出目录
├── data/db/           # SQLite 数据库
├── .env.example       # 环境变量模板
├── pyproject.toml     # 项目配置
└── README.md
```

## 小众分公式

```
niche_score = 0.35 × 播放量分 + 0.25 × 渗透率分 + 0.25 × 艺人独立分 + 0.15 × 流派稀有度
```

## 免责声明

本工具仅供娱乐，AI 锐评内容不代表客观评价。网易云音乐相关数据接口可能因平台策略变更而失效。

---

<p align="center">「わたくしの審判を受ける覚悟はあって？ 跌丝袜。」</p>
