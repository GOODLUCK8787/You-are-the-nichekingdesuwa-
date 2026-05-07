from yinyue.api.models import Song


def score(song: Song, all_songs: list[Song]) -> float:
    """Score by artist obscurity. Estimates artist popularity from songs in the playlist."""
    artist_names = {a.name for a in song.artists}
    if not artist_names:
        return 0.5

    # Collect popularity of all songs by the same artist(s) in this playlist
    artist_pops = []
    for s in all_songs:
        s_artist_names = {a.name for a in s.artists}
        if artist_names & s_artist_names:
            artist_pops.append(s.popularity)

    if not artist_pops:
        return 0.85  # Artist not found in batch → likely obscure

    avg_pop = sum(artist_pops) / len(artist_pops)
    return round(1.0 - (avg_pop / 100.0) ** 0.5, 4)
