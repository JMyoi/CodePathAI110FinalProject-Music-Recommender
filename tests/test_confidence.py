from src.confidence import compute_confidence
from src.recommender import Recommender, Song, UserProfile


def make_catalog():
    return [
        Song(id=1, title="Pop Match", artist="A", genre="pop", mood="happy",
             energy=0.8, tempo_bpm=120, valence=0.9, danceability=0.8, acousticness=0.2),
        Song(id=2, title="Pop Other", artist="B", genre="pop", mood="chill",
             energy=0.5, tempo_bpm=100, valence=0.7, danceability=0.7, acousticness=0.3),
        Song(id=3, title="Lofi Track", artist="C", genre="lofi", mood="chill",
             energy=0.3, tempo_bpm=80, valence=0.5, danceability=0.5, acousticness=0.9),
    ]


def _pop_user():
    return UserProfile(favorite_genre="pop", favorite_mood="happy",
                       target_energy=0.8, likes_acoustic=False)


def _metal_user():
    return UserProfile(favorite_genre="metal", favorite_mood="intense",
                       target_energy=0.9, likes_acoustic=False)


def test_confidence_in_zero_to_one_range():
    songs = make_catalog()
    rec = Recommender(songs)
    user = _pop_user()
    ranked = rec.score_all(user)
    for sc in ranked:
        result = compute_confidence(user, sc.song, songs, ranked)
        assert 0.0 <= result.value <= 1.0


def test_confidence_drops_when_genre_absent_from_catalog():
    songs = make_catalog()
    rec = Recommender(songs)

    pop_user = _pop_user()
    metal_user = _metal_user()

    pop_ranked = rec.score_all(pop_user)
    metal_ranked = rec.score_all(metal_user)

    pop_top = compute_confidence(pop_user, pop_ranked[0].song, songs, pop_ranked)
    metal_top = compute_confidence(metal_user, metal_ranked[0].song, songs, metal_ranked)

    assert pop_top.value > metal_top.value
    assert metal_top.breakdown["catalog_fit"] == 0.0


def test_higher_coverage_means_higher_confidence_when_score_close():
    songs = make_catalog()
    rec = Recommender(songs)
    user = _pop_user()
    ranked = rec.score_all(user)

    full_match = next(s for s in songs if s.id == 1)
    partial_match = next(s for s in songs if s.id == 2)

    full = compute_confidence(user, full_match, songs, ranked)
    partial = compute_confidence(user, partial_match, songs, ranked)

    assert full.breakdown["coverage"] > partial.breakdown["coverage"]
    assert full.value > partial.value


def test_confidence_breakdown_keys():
    songs = make_catalog()
    rec = Recommender(songs)
    user = _pop_user()
    ranked = rec.score_all(user)
    result = compute_confidence(user, ranked[0].song, songs, ranked)
    assert set(result.breakdown.keys()) == {"coverage", "margin", "catalog_fit"}
