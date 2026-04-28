from pathlib import Path

from src.recommender import Song, load_songs

CSV = Path(__file__).resolve().parent.parent / "data" / "songs.csv"


def test_load_songs_returns_full_catalog():
    songs = load_songs(str(CSV))
    assert len(songs) == 40
    assert all(isinstance(s, Song) for s in songs)


def test_load_songs_has_diverse_genres():
    songs = load_songs(str(CSV))
    genres = {s.genre for s in songs}
    assert len(genres) >= 10
    assert "metal" not in genres
    assert "k-pop" not in genres


def test_load_songs_parses_numeric_columns():
    songs = load_songs(str(CSV))
    sample = songs[0]
    assert isinstance(sample.energy, float)
    assert isinstance(sample.tempo_bpm, float)
    assert 0.0 <= sample.energy <= 1.0
    assert 0.0 <= sample.acousticness <= 1.0


def test_load_songs_preserves_titles():
    songs = load_songs(str(CSV))
    titles = {s.title for s in songs}
    assert "I Wanna Dance with Somebody" in titles
    assert "Weightless" in titles
