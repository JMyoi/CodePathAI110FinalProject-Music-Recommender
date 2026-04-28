# 🎵 VibeFinder — Music Recommender with Self-Critique

## Project Summary

VibeFinder is a small content-based music recommender extended with a **confidence score** and an **LLM self-critique loop** for the AI110 Module 3 final project. Given a user's taste profile (favorite genre, favorite mood, target energy, acoustic preference), it scores songs from a 40-song catalog covering 17 genres, returns the top *k*, and then has an AI critic review its own picks and flag weak ones. The whole thing is wrapped in a Streamlit UI for the class demo.

The project explores how a recommender can not only *make* predictions but also *evaluate its own reliability* — and where that reliability breaks down.

---

## How the System Works

There are three layers:

1. **Scoring (`src/recommender.py`)** — every song gets a score against the user profile:
   - `+2.0` if genre matches
   - `+1.5` if mood matches
   - `-|song.energy - target_energy|` (closer is better)
   - `±0.5` for acoustic preference alignment

2. **Confidence (`src/confidence.py`)** — every recommendation gets a 0–1 confidence value, blending three deterministic signals:
   - **Coverage** — fraction of the user's stated preferences this song actually hits
   - **Margin** — score gap to the next-ranked song (ties → unsure)
   - **Catalog fit** — how well-represented the user's favorite genre is in the catalog (if no songs match the genre at all, confidence collapses)

3. **Self-critique (`src/critic.py`)** — after the top *k* is picked, a critic reviews the whole batch:
   - `OpenAICritic` calls `gpt-4o-mini` with the profile + picks and asks for a verdict (`strong` / `ok` / `weak`), an overall note, and a one-line per-song note. Uses JSON mode for reliable parsing.
   - `HeuristicCritic` is a no-LLM fallback that derives the same shape from the confidence breakdowns. Used automatically when `OPENAI_API_KEY` is unset.

---

## Getting Started

### Setup

1. Create a virtual environment:

   ```bash
   python -m venv .venv
   source .venv/bin/activate      # Mac or Linux
   .venv\Scripts\activate         # Windows
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. (Optional) Add your OpenAI key for the LLM critic:

   ```bash
   cp .env.example .env
   # then edit .env and paste your OPENAI_API_KEY
   ```

   Without a key, the app falls back to the heuristic critic.

### Run the CLI

```bash
python -m src.main
```

### Run the Streamlit UI

```bash
streamlit run src/app.py
```

### Run the tests

```bash
pytest
```

---

## Experiments You Can Try

- **Ask for a missing genre.** Set `favorite_genre="metal"` (deliberately absent from the catalog, along with k-pop and trap). Watch `catalog_fit` collapse to 0 and the critic flag the picks as `weak` — even though the catalog has 40 songs across 17 genres.
- **Tweak the genre weight.** In `src/recommender.py`, change `GENRE_WEIGHT` from `2.0` to `0.5`. Notice how mood-matching songs now lead, and the confidence breakdown shifts toward coverage rather than margin.
- **Compare critics.** Run with and without `OPENAI_API_KEY` set. The LLM critic is more nuanced ("good for a workout, but the energy is too high if you're trying to focus") while the heuristic is more mechanical.
- **Ties.** Pick a profile where two songs tie on score — confidence drops because the margin term goes to zero.

---

## Limitations and Risks

- **Limited catalog (40 songs across 17 genres).** Better than the 10-song starter, but still small enough that some genres only have one or two songs. The catalog-fit term is doing real work.
- **Hard-coded weights.** Genre and mood weights are heuristic — the system never learns from feedback.
- **LLM critic is not ground truth.** It can confidently rationalize bad picks. The heuristic critic is more transparent but also more rigid.
- **Demographic blindness.** No notion of who the listener is beyond the four preference fields. Cultural and language context are absent.
- **Self-critique can mask issues.** A "strong" verdict from the model doesn't mean the recommendation is actually good — it just means the model thinks so.

A deeper version of this discussion lives in [model_card.md](model_card.md).

---

## Reflection

See [model_card.md](model_card.md) for the full reflection.

The most interesting thing I learned is that adding a confidence score is **way more useful than adding an LLM critic** for a system this small. The deterministic confidence catches the catalog-fit failure mode immediately and visibly, while the LLM critic, given the same inputs, will sometimes over-justify weak picks. That mirrors a real concern with AI evaluation: a model evaluating its own outputs is structurally biased toward agreement.
