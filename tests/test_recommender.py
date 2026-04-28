from src.recommender import Recommender, Song, UserProfile, recommend_songs


def make_small_recommender() -> Recommender:
    songs = [
        Song(id=1, title="Test Pop Track", artist="Test Artist", genre="pop", mood="happy",
             energy=0.8, tempo_bpm=120, valence=0.9, danceability=0.8, acousticness=0.2),
        Song(id=2, title="Chill Lofi Loop", artist="Test Artist", genre="lofi", mood="chill",
             energy=0.4, tempo_bpm=80, valence=0.6, danceability=0.5, acousticness=0.9),
    ]
    return Recommender(songs)


def _pop_user() -> UserProfile:
    return UserProfile(favorite_genre="pop", favorite_mood="happy",
                       target_energy=0.8, likes_acoustic=False)


def test_recommend_returns_songs_sorted_by_score():
    rec = make_small_recommender()
    results = rec.recommend(_pop_user(), k=2)
    assert len(results) == 2
    assert results[0].genre == "pop"
    assert results[0].mood == "happy"


def test_explain_recommendation_returns_non_empty_string():
    rec = make_small_recommender()
    explanation = rec.explain_recommendation(_pop_user(), rec.songs[0])
    assert isinstance(explanation, str)
    assert explanation.strip() != ""


def test_explain_mentions_matching_features():
    rec = make_small_recommender()
    explanation = rec.explain_recommendation(_pop_user(), rec.songs[0])
    assert "pop" in explanation
    assert "happy" in explanation


def test_recommend_songs_functional_api_returns_dicts():
    rec = make_small_recommender()
    songs_as_dicts = [s.__dict__ for s in rec.songs]
    user_prefs = {"genre": "pop", "mood": "happy", "energy": 0.8, "likes_acoustic": False}
    results = recommend_songs(user_prefs, songs_as_dicts, k=2)
    assert len(results) == 2
    song, score, explanation = results[0]
    assert isinstance(song, dict)
    assert isinstance(score, float)
    assert isinstance(explanation, str)
    assert song["genre"] == "pop"


def test_disliking_acoustic_penalizes_acoustic_songs():
    rec = make_small_recommender()
    user_dislikes_acoustic = UserProfile(favorite_genre="pop", favorite_mood="happy",
                                         target_energy=0.8, likes_acoustic=False)
    user_likes_acoustic = UserProfile(favorite_genre="pop", favorite_mood="happy",
                                      target_energy=0.8, likes_acoustic=True)
    lofi_song = rec.songs[1]
    score_dislike, _ = rec._score(user_dislikes_acoustic, lofi_song)
    score_like, _ = rec._score(user_likes_acoustic, lofi_song)
    assert score_like > score_dislike
