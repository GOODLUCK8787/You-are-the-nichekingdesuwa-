import math

# Reference: play count of a top-tier viral hit on NetEase
REF_MAX_PLAY_COUNT = 10_000_000
REF_LOG = math.log10(1 + REF_MAX_PLAY_COUNT)


def score(play_count: int) -> float:
    """Score a song by how few plays it has. 1.0 = very few plays (niche), 0.0 = viral."""
    if play_count <= 0:
        return 0.85  # Unknown play count — lean toward niche
    return round(max(0.0, min(1.0, 1.0 - math.log10(1 + play_count) / REF_LOG)), 4)
