GENRE_RARITY = {
    "流行": 0.05,
    "摇滚": 0.25,
    "电子": 0.20,
    "民谣": 0.30,
    "说唱": 0.15,
    "古典": 0.70,
    "爵士": 0.75,
    "世界音乐": 0.90,
    "后摇": 0.80,
    "独立": 0.70,
    "金属": 0.85,
    "实验": 0.95,
    "雷鬼": 0.85,
    "布鲁斯": 0.90,
    "古风": 0.20,
    "二次元": 0.10,
    "轻音乐": 0.35,
}

DEFAULT_RARITY = 0.50


def score(genre_tags: list[str]) -> float:
    """Score by genre rarity. Takes the max rarity among all tags."""
    if not genre_tags:
        return DEFAULT_RARITY
    return round(max(GENRE_RARITY.get(tag, DEFAULT_RARITY) for tag in genre_tags), 4)
