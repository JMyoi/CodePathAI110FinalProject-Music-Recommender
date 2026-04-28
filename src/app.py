import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st
from dotenv import load_dotenv

from src.confidence import compute_confidence
from src.critic import HeuristicCritic, OpenAICritic, Recommendation
from src.recommender import Recommender, UserProfile, load_songs

load_dotenv()

DATA_PATH = ROOT / "data" / "songs.csv"

VERDICT_COLORS = {"strong": "#2e7d32", "ok": "#f9a825", "weak": "#c62828"}


@st.cache_data
def cached_songs(path: str):
    return load_songs(path)


def main() -> None:
    st.set_page_config(page_title="VibeFinder", page_icon="🎵", layout="wide")
    st.title("🎵 VibeFinder — with confidence + self-critique")
    st.caption("AI110 Module 3 final project demo")

    songs = cached_songs(str(DATA_PATH))
    genres = sorted({s.genre for s in songs})
    moods = sorted({s.mood for s in songs})

    with st.sidebar:
        st.header("Your taste profile")
        genre_choice = st.selectbox("Favorite genre", options=genres + ["(custom)"])
        if genre_choice == "(custom)":
            favorite_genre = st.text_input("Enter a custom genre", value="metal")
        else:
            favorite_genre = genre_choice
        favorite_mood = st.selectbox("Favorite mood", options=moods)
        target_energy = st.slider("Target energy", 0.0, 1.0, 0.7, 0.05)
        likes_acoustic = st.checkbox("I like acoustic songs", value=False)
        k = st.slider("How many recommendations?", 1, 10, 5)
        st.divider()
        api_key_present = bool(os.environ.get("OPENAI_API_KEY"))
        use_llm = st.toggle(
            "Use LLM critic (OpenAI)",
            value=api_key_present,
            disabled=not api_key_present,
            help="Requires OPENAI_API_KEY in your environment.",
        )
        if not api_key_present:
            st.caption("No `OPENAI_API_KEY` set — using the heuristic critic.")

    user = UserProfile(
        favorite_genre=favorite_genre,
        favorite_mood=favorite_mood,
        target_energy=target_energy,
        likes_acoustic=likes_acoustic,
    )

    rec_engine = Recommender(songs)
    ranked = rec_engine.score_all(user)
    top = ranked[:k]

    recs = []
    for sc in top:
        conf = compute_confidence(user, sc.song, songs, ranked)
        recs.append(Recommendation(scored=sc, confidence=conf))

    if use_llm:
        try:
            critic = OpenAICritic()
        except Exception as e:
            st.warning(f"LLM critic unavailable ({e}). Falling back to heuristic.")
            critic = HeuristicCritic()
    else:
        critic = HeuristicCritic()

    with st.spinner("Critiquing recommendations..."):
        critique = critic.critique(user, recs)

    st.subheader("Top recommendations")
    for r in recs:
        s = r.scored.song
        with st.container(border=True):
            cols = st.columns([3, 2])
            with cols[0]:
                st.markdown(f"### {s.title}")
                st.markdown(f"*by {s.artist}* — `{s.genre}` / `{s.mood}`")
                st.write(rec_engine.explain_recommendation(user, s))
                note = critique.per_song_notes.get(s.id)
                if note:
                    st.markdown(f"🧠 **Critic:** {note}")
            with cols[1]:
                st.metric("Score", f"{r.scored.score:.2f}")
                st.progress(r.confidence.value, text=f"Confidence: {r.confidence.value:.2f}")
                with st.expander("Confidence breakdown"):
                    for label, val in r.confidence.breakdown.items():
                        st.write(f"{label}: {val:.2f}")

    st.subheader("Critic's overall take")
    color = VERDICT_COLORS.get(critique.verdict, "#555")
    st.markdown(
        f"<span style='background:{color};color:white;padding:4px 10px;"
        f"border-radius:12px;font-weight:600'>{critique.verdict.upper()}</span>",
        unsafe_allow_html=True,
    )
    st.write(critique.overall_note)


if __name__ == "__main__":
    main()
