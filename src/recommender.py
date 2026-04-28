import csv
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Tuple

GENRE_WEIGHT = 2.0
MOOD_WEIGHT = 1.5
ENERGY_WEIGHT = 1.0
ACOUSTIC_BONUS = 0.5
ACOUSTICNESS_THRESHOLD = 0.6


@dataclass
class Song:
    id: int
    title: str
    artist: str
    genre: str
    mood: str
    energy: float
    tempo_bpm: float
    valence: float
    danceability: float
    acousticness: float


@dataclass
class UserProfile:
    favorite_genre: str
    favorite_mood: str
    target_energy: float
    likes_acoustic: bool


@dataclass
class ScoredSong:
    song: Song
    score: float
    reasons: List[str] = field(default_factory=list)


class Recommender:
    def __init__(self, songs: List[Song]):
        self.songs = songs

    def _score(self, user: UserProfile, song: Song) -> Tuple[float, List[str]]:
        score = 0.0
        reasons: List[str] = []

        if song.genre == user.favorite_genre:
            score += GENRE_WEIGHT
            reasons.append(f"matches your favorite genre ({song.genre})")

        if song.mood == user.favorite_mood:
            score += MOOD_WEIGHT
            reasons.append(f"matches your favorite mood ({song.mood})")

        energy_gap = abs(song.energy - user.target_energy)
        score -= ENERGY_WEIGHT * energy_gap
        if energy_gap < 0.15:
            reasons.append(f"energy ({song.energy:.2f}) close to your target ({user.target_energy:.2f})")

        if user.likes_acoustic and song.acousticness > ACOUSTICNESS_THRESHOLD:
            score += ACOUSTIC_BONUS
            reasons.append(f"acoustic feel (acousticness={song.acousticness:.2f})")
        elif (not user.likes_acoustic) and song.acousticness > ACOUSTICNESS_THRESHOLD:
            score -= ACOUSTIC_BONUS

        return score, reasons

    def score_all(self, user: UserProfile) -> List[ScoredSong]:
        scored = [
            ScoredSong(song=s, score=score, reasons=reasons)
            for s in self.songs
            for score, reasons in [self._score(user, s)]
        ]
        scored.sort(key=lambda x: x.score, reverse=True)
        return scored

    def recommend(self, user: UserProfile, k: int = 5) -> List[Song]:
        return [sc.song for sc in self.score_all(user)[:k]]

    def recommend_scored(self, user: UserProfile, k: int = 5) -> List[ScoredSong]:
        return self.score_all(user)[:k]

    def explain_recommendation(self, user: UserProfile, song: Song) -> str:
        _, reasons = self._score(user, song)
        if not reasons:
            return f"'{song.title}' is a fallback pick — it didn't match your stated preferences strongly."
        return f"'{song.title}' " + "; ".join(reasons) + "."


def _user_from_dict(prefs: Dict) -> UserProfile:
    return UserProfile(
        favorite_genre=prefs.get("genre", ""),
        favorite_mood=prefs.get("mood", ""),
        target_energy=float(prefs.get("energy", 0.5)),
        likes_acoustic=bool(prefs.get("likes_acoustic", False)),
    )


def _song_from_row(row: Dict) -> Song:
    return Song(
        id=int(row["id"]),
        title=row["title"],
        artist=row["artist"],
        genre=row["genre"],
        mood=row["mood"],
        energy=float(row["energy"]),
        tempo_bpm=float(row["tempo_bpm"]),
        valence=float(row["valence"]),
        danceability=float(row["danceability"]),
        acousticness=float(row["acousticness"]),
    )


def load_songs(csv_path: str) -> List[Song]:
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return [_song_from_row(row) for row in reader]


def score_song(user_prefs: Dict, song) -> Tuple[float, List[str]]:
    user = _user_from_dict(user_prefs)
    song_obj = song if isinstance(song, Song) else _song_from_row(song)
    rec = Recommender([song_obj])
    return rec._score(user, song_obj)


def recommend_songs(user_prefs: Dict, songs: List, k: int = 5) -> List[Tuple[Dict, float, str]]:
    user = _user_from_dict(user_prefs)
    song_objs = [s if isinstance(s, Song) else _song_from_row(s) for s in songs]
    rec = Recommender(song_objs)
    out: List[Tuple[Dict, float, str]] = []
    for scored in rec.recommend_scored(user, k):
        explanation = rec.explain_recommendation(user, scored.song)
        out.append((asdict(scored.song), scored.score, explanation))
    return out
