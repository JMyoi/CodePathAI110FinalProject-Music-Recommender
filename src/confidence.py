from dataclasses import dataclass, field
from typing import Dict, List

from src.recommender import ScoredSong, Song, UserProfile

COVERAGE_WEIGHT = 0.5
MARGIN_WEIGHT = 0.25
CATALOG_FIT_WEIGHT = 0.25

ENERGY_BUCKET_TOLERANCE = 0.2


@dataclass
class ConfidenceResult:
    value: float
    breakdown: Dict[str, float] = field(default_factory=dict)


def _coverage(user: UserProfile, song: Song) -> float:
    hits = 0
    total = 4
    if song.genre == user.favorite_genre:
        hits += 1
    if song.mood == user.favorite_mood:
        hits += 1
    if abs(song.energy - user.target_energy) <= ENERGY_BUCKET_TOLERANCE:
        hits += 1
    if user.likes_acoustic == (song.acousticness > 0.6):
        hits += 1
    return hits / total


def _margin(rank: int, ranked: List[ScoredSong]) -> float:
    if rank >= len(ranked) - 1:
        return 0.5
    gap = ranked[rank].score - ranked[rank + 1].score
    return max(0.0, min(1.0, gap / 2.0))


def _catalog_fit(user: UserProfile, all_songs: List[Song]) -> float:
    if not all_songs:
        return 0.0
    matches = sum(1 for s in all_songs if s.genre == user.favorite_genre)
    if matches == 0:
        return 0.0
    return min(1.0, matches / 3.0)


def compute_confidence(
    user: UserProfile,
    song: Song,
    all_songs: List[Song],
    ranked: List[ScoredSong],
) -> ConfidenceResult:
    rank = next((i for i, sc in enumerate(ranked) if sc.song.id == song.id), len(ranked) - 1)

    coverage = _coverage(user, song)
    margin = _margin(rank, ranked)
    catalog_fit = _catalog_fit(user, all_songs)

    value = (
        COVERAGE_WEIGHT * coverage
        + MARGIN_WEIGHT * margin
        + CATALOG_FIT_WEIGHT * catalog_fit
    )
    value = max(0.0, min(1.0, value))

    return ConfidenceResult(
        value=value,
        breakdown={
            "coverage": coverage,
            "margin": margin,
            "catalog_fit": catalog_fit,
        },
    )
