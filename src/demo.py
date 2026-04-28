"""
End-to-end demo for VibeFinder.

Runs three contrasting user profiles through the full pipeline
(scoring → confidence → self-critique) and prints clearly labeled
output for each. This is the script used in the video walkthrough.

Run with:
    python -m src.demo
"""

from dataclasses import dataclass

from dotenv import load_dotenv

from src.confidence import compute_confidence
from src.critic import Recommendation, make_critic
from src.recommender import Recommender, UserProfile, load_songs


@dataclass
class Scenario:
    name: str
    purpose: str
    user: UserProfile


SCENARIOS = [
    Scenario(
        name="1. Happy path",
        purpose="The catalog has good coverage for this profile. We expect HIGH confidence and a STRONG verdict.",
        user=UserProfile(
            favorite_genre="pop",
            favorite_mood="happy",
            target_energy=0.8,
            likes_acoustic=False,
        ),
    ),
    Scenario(
        name="2. Partial coverage",
        purpose="The catalog has SOME jazz but only one 'relaxed' jazz track. Expect MID confidence and an OK verdict.",
        user=UserProfile(
            favorite_genre="jazz",
            favorite_mood="relaxed",
            target_energy=0.4,
            likes_acoustic=True,
        ),
    ),
    Scenario(
        name="3. Failure mode (guardrail demo)",
        purpose="The catalog has no metal. The guardrail should catch this: catalog_fit collapses to 0.00 and the critic says WEAK.",
        user=UserProfile(
            favorite_genre="metal",
            favorite_mood="intense",
            target_energy=0.9,
            likes_acoustic=False,
        ),
    ),
]


VERDICT_BADGES = {"strong": "[STRONG]", "ok": "[  OK  ]", "weak": "[ WEAK ]"}


def print_header(text: str, char: str = "=") -> None:
    print()
    print(char * 78)
    print(text)
    print(char * 78)


def print_scenario(scenario: Scenario, songs, engine: Recommender, critic, k: int = 5) -> None:
    print_header(scenario.name)
    u = scenario.user
    print(f"Purpose: {scenario.purpose}")
    print()
    print(f"User profile:")
    print(f"  favorite_genre = {u.favorite_genre!r}")
    print(f"  favorite_mood  = {u.favorite_mood!r}")
    print(f"  target_energy  = {u.target_energy}")
    print(f"  likes_acoustic = {u.likes_acoustic}")

    ranked = engine.score_all(u)
    top = ranked[:k]
    recs = [
        Recommendation(scored=sc, confidence=compute_confidence(u, sc.song, songs, ranked))
        for sc in top
    ]
    critique = critic.critique(u, recs)

    print()
    print(f"Top {k} recommendations:")
    print(f"  {'#':<2} {'Title':32s} {'Artist':22s} {'Genre':12s} {'Score':>6s} {'Conf':>6s} {'CatFit':>7s}")
    print(f"  {'-'*2:<2} {'-'*32} {'-'*22} {'-'*12} {'-'*6:>6} {'-'*6:>6} {'-'*7:>7}")
    for i, r in enumerate(recs, start=1):
        s = r.scored.song
        cf = r.confidence.breakdown["catalog_fit"]
        print(
            f"  {i:<2} {s.title[:32]:32s} {s.artist[:22]:22s} {s.genre[:12]:12s} "
            f"{r.scored.score:>6.2f} {r.confidence.value:>6.2f} {cf:>7.2f}"
        )

    print()
    badge = VERDICT_BADGES.get(critique.verdict, f"[{critique.verdict}]")
    print(f"Critic verdict: {badge}")
    print(f"  {critique.overall_note}")
    if critique.per_song_notes:
        print()
        print("Per-song critic notes:")
        for r in recs:
            note = critique.per_song_notes.get(r.scored.song.id, "(none)")
            print(f"  - {r.scored.song.title}: {note}")


def main() -> None:
    load_dotenv()
    songs = load_songs("data/songs.csv")
    engine = Recommender(songs)
    critic = make_critic()

    print_header("VibeFinder — End-to-End Demo", char="#")
    print(f"Catalog: {len(songs)} songs across {len({s.genre for s in songs})} genres")
    print(f"Critic:  {type(critic).__name__}")
    print()
    print("Running three contrasting profiles to demonstrate scoring,")
    print("confidence-based reliability, and the self-critique loop.")

    for scenario in SCENARIOS:
        print_scenario(scenario, songs, engine, critic)

    print_header("Summary", char="#")
    print("Scenario 1 should show HIGH confidence + STRONG verdict.")
    print("Scenario 2 should show MID confidence + OK verdict.")
    print("Scenario 3 should show LOW confidence + WEAK verdict (guardrail caught a missing genre).")


if __name__ == "__main__":
    main()
