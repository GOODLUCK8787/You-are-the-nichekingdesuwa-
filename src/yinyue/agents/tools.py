"""Tool definitions for agent function calling. Each tool has an OpenAI-compatible schema."""

FETCH_PLAYLIST = {
    "type": "function",
    "function": {
        "name": "fetch_playlist",
        "description": "扒取网易云歌单数据：输入歌单URL，返回歌单名称、创建者、全部歌曲列表、每首歌的播放量和热度信息",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "歌单链接，例如 https://music.163.com/playlist?id=3136952023"}
            },
            "required": ["url"]
        }
    }
}

ASK_USER = {
    "type": "function",
    "function": {
        "name": "ask_user",
        "description": "向用户提问。根据歌单内容动态生成3-5个问题，了解歌单背后的故事、场景和用户的真实想法。回答将用于后续分析和锐评。",
        "parameters": {
            "type": "object",
            "properties": {
                "questions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string", "description": "问题ID如q1"},
                            "question": {"type": "string", "description": "问题内容（祥子语气）"},
                            "tone": {"type": "string", "description": "语气：审视/好奇/讽刺/赞赏"}
                        },
                        "required": ["id", "question"]
                    }
                }
            },
            "required": ["questions"]
        }
    }
}

COMPUTE_SCORES = {
    "type": "function",
    "function": {
        "name": "compute_scores",
        "description": "计算歌单中每首歌的小众分数，综合播放量、热度、艺人知名度、流派稀有度四个维度",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
}

GENERATE_ROAST = {
    "type": "function",
    "function": {
        "name": "generate_roast",
        "description": "生成祥子风格的毒舌锐评。结合歌单数据、小众分排行、用户回答，对歌单主人的音乐品味进行审判。",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
}

RENDER_PDF = {
    "type": "function",
    "function": {
        "name": "render_pdf",
        "description": "将分析结果渲染为PDF报告并保存",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
}

ALL_TOOLS = [FETCH_PLAYLIST, ASK_USER, COMPUTE_SCORES, GENERATE_ROAST, RENDER_PDF]
