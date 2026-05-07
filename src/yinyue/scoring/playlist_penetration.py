def score(popularity: float) -> float:
    """Score by platform popularity (0-100). High popularity = low niche score."""
    if popularity <= 0:
        return 0.85
    return round(1.0 - (popularity / 100.0) ** 0.6, 4)
