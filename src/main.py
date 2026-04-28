"""
Command line runner for the Music Recommender Simulation.

Run with: python -m src.main
"""

from dotenv import load_dotenv

from src.confidence import compute_confidence
from src.critic import Recommendation, make_critic
from src.recommender import Recommender, UserProfile, load_songs


def main() -> None:
    load_dotenv()

    songs = load_songs("data/songs.csv")
    user = UserProfile(
        favorite_genre="pop",
        favorite_mood="happy",
        target_energy=0.8,
        likes_acoustic=False,
    )

    engine = Recommender(songs)
    ranked = engine.score_all(user)
    top = ranked[:5]

    recs = [
        Recommendation(scored=sc, confidence=compute_confidence(user, sc.song, songs, ranked))
        for sc in top
    ]

    critic = make_critic()
    critique = critic.critique(user, recs)

    print("\nTop recommendations:\n")
    for r in recs:
        s = r.scored.song
        explanation = engine.explain_recommendation(user, s)
        note = critique.per_song_notes.get(s.id, "")
        print(f"{s.title} by {s.artist}")
        print(f"  Score: {r.scored.score:.2f}  Confidence: {r.confidence.value:.2f}")
        print(f"  Because: {explanation}")
        if note:
            print(f"  Critic: {note}")
        print()

    print(f"Critic's overall verdict: {critique.verdict.upper()}")
    print(f"  {critique.overall_note}")


if __name__ == "__main__":
    main()
