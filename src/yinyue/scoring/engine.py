from yinyue.api.models import Song, NicheScores
from yinyue.scoring import play_count, playlist_penetration, artist_indie, genre_rarity

# Weights: play_count dominates, then penetration + artist, then genre
WEIGHTS = (0.35, 0.25, 0.25, 0.15)


def compute_all(songs: list[Song]) -> list[NicheScores]:
    """Compute niche scores for all songs in a playlist."""
    results = []
    for song in songs:
        s_pc = play_count.score(song.play_count)
        s_pp = playlist_penetration.score(song.popularity)
        s_ai = artist_indie.score(song, songs)
        s_gr = genre_rarity.score(song.genre_tags)

        overall = (
            WEIGHTS[0] * s_pc
            + WEIGHTS[1] * s_pp
            + WEIGHTS[2] * s_ai
            + WEIGHTS[3] * s_gr
        )

        overall_clamped = max(0.0, min(1.0, overall))
        results.append(NicheScores(
            song_netease_id=song.netease_id,
            overall_score=round(overall_clamped, 4),
            play_count_score=s_pc,
            penetration_score=s_pp,
            artist_indie_score=s_ai,
            genre_rarity_score=s_gr,
        ))

    # Compute percentile ranks within the batch
    if results:
        sorted_scores = sorted(r.overall_score for r in results)
        n = len(sorted_scores)
        for r in results:
            rank = sum(1 for s in sorted_scores if s <= r.overall_score)
            r.percentile_rank = round(rank / n * 100, 1)

    return results
