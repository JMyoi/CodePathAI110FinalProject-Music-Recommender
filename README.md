# 🎵 VibeFinder — Music Recommender with Self-Critique

Loom Link: https://www.loom.com/share/82db64c9edd241a7b710539561666fe3

A music recommender extended with a confidence score and an LLM self-critique loop. Built for AI110 Module 3 final project.

> **Companion docs:** [howItWorks.md](howItWorks.md) (architecture deep-dive) · [model_card.md](model_card.md) (model card) · [REFLECTION.md](REFLECTION.md) (AI-collaboration reflection) · [presentation.md](presentation.md) (5-minute talk script)

---

## 1. The Original Project (and what I extended)

**Original starter project:** *Music Recommender Simulation* (AI110 Module 3 starter). The starter provided a stub recommender system with:

- A 10-song CSV catalog (`data/songs.csv`) with audio-feature columns (energy, tempo, valence, danceability, acousticness)
- A skeleton `Recommender` class with empty `recommend()` and `explain_recommendation()` methods
- A starter functional API (`load_songs`, `score_song`, `recommend_songs`) — also empty
- Two starter pytest tests asserting basic shape

**Original goal:** demonstrate a small content-based recommender — given a user profile (favorite genre, favorite mood, target energy, acoustic preference), score songs and return the top *k*.

**What I added:** the recommender by itself was a one-day exercise. The interesting question was *can the system know when not to trust itself?* So I built three things on top of the starter:

1. **A deterministic confidence score** per recommendation (0–1), blending coverage / margin / catalog-fit.
2. **A self-critique layer** — `OpenAICritic` (gpt-4o-mini) reviews the top-k as a batch and emits a verdict + per-song notes; `HeuristicCritic` is a deterministic fallback.
3. **A Streamlit UI + a multi-scenario demo script** so the behavior is visible and reproducible.

I also expanded the catalog from 10 → 40 real songs across 17 genres (deliberately omitting metal, k-pop, and trap to preserve a missing-genre failure-mode demo), filled in the original stubs, and grew the test suite from 2 → 20 tests.

---

## 2. System Architecture

```
            data/songs.csv  (40 rows, 17 genres)
                       │
                       ▼
   ┌──────────────────────────────────────┐
   │  Layer 1 — SCORING                    │   src/recommender.py
   │  Rule-based deterministic scorer.     │
   │  Genre, mood, energy distance,        │   Recommender._score(user, song)
   │  acoustic alignment.                  │   → (score, reasons[])
   └──────────────────────────────────────┘
                       │
                       │  list[ScoredSong] sorted by score
                       ▼
   ┌──────────────────────────────────────┐
   │  Layer 2 — CONFIDENCE (guardrail)     │   src/confidence.py
   │  0–1 trust value per pick.            │
   │  coverage + margin + catalog_fit      │   compute_confidence(...)
   │  → ConfidenceResult                   │   → ConfidenceResult
   └──────────────────────────────────────┘
                       │
                       │  list[Recommendation]
                       ▼
   ┌──────────────────────────────────────┐
   │  Layer 3 — SELF-CRITIQUE (AI feature) │   src/critic.py
   │  Reviews the whole batch.             │
   │  • OpenAICritic  → gpt-4o-mini        │   critic.critique(user, recs)
   │  • HeuristicCritic → no-LLM fallback  │   → CritiqueResult
   │  Selected by make_critic() based on   │
   │  presence of OPENAI_API_KEY.          │
   └──────────────────────────────────────┘
                       │
                       │  CritiqueResult (verdict, overall_note, per_song_notes)
                       ▼
        ┌──────────────────────────┐
        │  CLI       Streamlit UI  │   src/main.py · src/app.py · src/demo.py
        │  src/demo.py  (3 scenes) │
        └──────────────────────────┘
```

Diagram matches the implementation 1:1; see [howItWorks.md](howItWorks.md) for a per-file walk-through and key-types diagram.

---

## 3. AI Feature

The substantial AI feature is the **self-critique + confidence loop** — a reliability harness that runs the recommender, evaluates its own output, and either certifies or flags it.

- `OpenAICritic` (in [src/critic.py](src/critic.py)) constructs a structured prompt containing the user profile and the top-k picks with their scores and reasons, calls `gpt-4o-mini` with `response_format={"type": "json_object"}`, and parses the response into a `CritiqueResult` containing a verdict (`strong` / `ok` / `weak`), an overall note, and a one-line note per song.
- The critic is integrated into the main pipeline (`make_critic()` in `src/critic.py`, called by `src/main.py`, `src/app.py`, and `src/demo.py`) — not an isolated demo.
- Behavior changes meaningfully: the critic re-frames the recommender's output as either trustworthy or suspect, with reasons; the deterministic confidence score does the same numerically.

The `Critic` Protocol means the LLM critic and the heuristic fallback are interchangeable, which keeps the demo runnable offline and lets the test suite mock the LLM cleanly.

---

## 4. Reliability / Guardrail

The reliability mechanism is the **confidence score** in [src/confidence.py](src/confidence.py), composed of three signals:

| Signal | What it catches |
|---|---|
| **Coverage** | The recommendation only matches some of the user's preferences. |
| **Margin** | The top pick barely beats the next one — basically a tie. |
| **Catalog fit** | The user's requested genre isn't in the catalog at all. |

If any of these collapse, the final confidence value collapses with them. The critic then uses these signals to issue a verdict — when `catalog_fit == 0`, the verdict is forced to `weak` and the per-song notes explicitly call out the wrong genre.

**This is demonstrated end-to-end by `python -m src.demo`** (see Sample I/O below) — three scenarios are run, and the third one (`metal` genre, absent from catalog) shows the guardrail catching the failure with a `WEAK` verdict and per-song notes saying *"Wrong genre (rock, not metal) — system fell back to feature similarity."*

---

## 5. Setup and How to Run

### Setup

1. Create a virtual environment:

   ```bash
   python -m venv .venv
   source .venv/bin/activate      # Mac / Linux
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

   Without a key, the app falls back to the heuristic critic — everything still runs.

### Run the demo (this is what the video walkthrough shows)

```bash
python -m src.demo
```

Runs three contrasting user profiles through the full pipeline and prints clearly labeled output for each scenario.

### Run the Streamlit UI

```bash
python -m streamlit run src/app.py
```

### Run the CLI (single scenario)

```bash
python -m src.main
```

### Run the tests

```bash
pytest
```

20 tests covering scoring, loading, confidence bounds + breakdown, critic shape (heuristic + mocked OpenAI), and several negative cases.

---

## 6. Sample Input / Output

The full output of `python -m src.demo` (three scenarios). This is the script run in the video walkthrough.

### Scenario 1 — Happy path

**Input:** `pop / happy / 0.8 energy / not acoustic`

**Output:**
```
Top 5 recommendations:
  #  Title                            Artist                 Genre         Score   Conf  CatFit
  -- -------------------------------- ---------------------- ------------ ------ ------ -------
  1  I Wanna Dance with Somebody      Whitney Houston        pop            3.45   0.94    1.00
  2  Born This Way                    Lady Gaga              pop            1.95   0.63    1.00
  3  Bad Romance                      Lady Gaga              pop            1.88   0.68    1.00
  4  i                                Kendrick Lamar         hip-hop        1.48   0.64    1.00
  5  Mr. Brightside                   The Killers            indie rock     1.37   0.63    1.00

Critic verdict: [STRONG]
  Top picks cover most of the user's stated preferences.
```

The system finds an excellent match (Whitney Houston, confidence 0.94). Notice slots 2-3 are both Lady Gaga — the system has no artist-diversity penalty, a known limitation.

### Scenario 2 — Partial coverage

**Input:** `jazz / relaxed / 0.4 energy / likes acoustic`

**Output:**
```
Top 5 recommendations:
  #  Title                            Artist                 Genre         Score   Conf  CatFit
  -- -------------------------------- ---------------------- ------------ ------ ------ -------
  1  Take Five                        Dave Brubeck Quartet   jazz           3.97   0.86    0.67
  2  What a Wonderful World           Louis Armstrong        jazz           2.40   0.63    0.67
  3  Clair de Lune                    Claude Debussy         classical      1.70   0.44    0.67
  4  Sittin' On The Dock of the Bay   Otis Redding           soul           1.50   0.42    0.67
  5  Pink + White                     Frank Ocean            r&b            1.45   0.54    0.67

Critic verdict: [  OK  ]
  Reasonable picks, but coverage of the user's preferences is partial.
```

Catalog has only one perfect-match jazz/relaxed track (Take Five). The system picks it, but everything after #2 is a stretch — confidence drops accordingly and the verdict is `OK`, not `STRONG`.

### Scenario 3 — Failure mode (the guardrail catches it)

**Input:** `metal / intense / 0.9 energy / not acoustic`

**Output:**
```
Top 5 recommendations:
  #  Title                            Artist                 Genre         Score   Conf  CatFit
  -- -------------------------------- ---------------------- ------------ ------ ------ -------
  1  Holiday                          Green Day              rock           1.49   0.38    0.00
  2  Bad Romance                      Lady Gaga              pop            1.48   0.38    0.00
  3  Harder Better Faster Stronger    Daft Punk              electronic     1.48   0.38    0.00
  4  Welcome to the Jungle            Guns N' Roses          rock           1.45   0.38    0.00
  5  Pride and Joy                    Stevie Ray Vaughan     blues          1.38   0.55    0.00

Critic verdict: [ WEAK ]
  No songs in the catalog match the requested genre 'metal'.
  These picks fell back to other features and should not be trusted.

Per-song critic notes:
  - Holiday: Wrong genre (rock, not metal) — system fell back to feature similarity.
  - Bad Romance: Wrong genre (pop, not metal) — system fell back to feature similarity.
  - Harder Better Faster Stronger: Wrong genre (electronic, not metal) — system fell back to feature similarity.
  - Welcome to the Jungle: Wrong genre (rock, not metal) — system fell back to feature similarity.
  - Pride and Joy: Wrong genre (blues, not metal) — system fell back to feature similarity.
```

This is the guardrail working as designed. The system *still* returns picks (it has to — the user asked for 5) but flags every pick as untrustworthy with a specific reason. Without the confidence + critic layer, the user would have gotten "Holiday by Green Day" with no warning that the system can't actually serve metal.

---

## 7. Experiments You Can Try

- **Ask for a missing genre.** Set `favorite_genre="metal"` — watch the guardrail trigger as in scenario 3.
- **Tweak the genre weight.** In `src/recommender.py`, change `GENRE_WEIGHT` from `2.0` to `0.5`. Mood-matching songs now lead, and the confidence breakdown shifts toward coverage rather than margin.
- **Compare critics.** Run with and without `OPENAI_API_KEY` set. The LLM critic gives more nuanced overall notes; the heuristic is more mechanical but reliably catches catalog-fit failures.
- **Ties.** Pick a profile where two songs tie on score — confidence drops because the margin term goes to zero.

---

## 8. Limitations

- **Limited catalog (40 songs across 17 genres).** Real recommenders work on millions; the catalog-fit term carries more weight here than it would at scale.
- **Hard-coded weights.** Genre and mood weights are heuristic — the system never learns from feedback.
- **LLM critic is not ground truth.** It can confidently rationalize bad picks. The heuristic critic is more reliable at *detecting* failures; the LLM is better at *describing* them.
- **No artist diversity penalty.** Visible in scenario 1 above (Born This Way + Bad Romance, both Lady Gaga, in adjacent slots).
- **Demographic blindness.** No notion of who the listener is beyond the four preference fields. Cultural and language context are absent.

A deeper discussion lives in [model_card.md](model_card.md). The reflection on AI-assisted development is in [REFLECTION.md](REFLECTION.md).

---

## 9. Repository Map

```
.
├── data/
│   └── songs.csv                40 real songs across 17 genres
├── src/
│   ├── __init__.py
│   ├── recommender.py           Layer 1: scoring (Song, UserProfile, Recommender)
│   ├── confidence.py            Layer 2: guardrail (compute_confidence, ConfidenceResult)
│   ├── critic.py                Layer 3: AI feature (HeuristicCritic, OpenAICritic, make_critic)
│   ├── main.py                  Single-scenario CLI runner
│   ├── demo.py                  Multi-scenario end-to-end demo (the video script)
│   └── app.py                   Streamlit UI
├── tests/
│   ├── test_recommender.py
│   ├── test_confidence.py
│   ├── test_critic.py           Includes mocked-OpenAI test
│   └── test_loading.py
├── conftest.py                  Adds project root to sys.path for pytest
├── requirements.txt
├── .env.example
├── README.md                    This file
├── howItWorks.md                Per-file architecture walk-through
├── model_card.md                Model card
├── REFLECTION.md                AI-collaboration reflection
└── presentation.md              5-minute talk script
```

---

## 10. Where Each Rubric Item Lives

| Rubric item | Where |
|---|---|
| Identification of base project + scope | §1 above ("The Original Project") |
| Substantial new AI feature | §3 above + [src/critic.py](src/critic.py) |
| Architecture diagram | §2 above + [howItWorks.md](howItWorks.md) |
| Functional end-to-end demo (2-3 inputs) | §6 above + `python -m src.demo` ([src/demo.py](src/demo.py)) |
| Reliability / guardrail + examples | §4 above + scenario 3 in §6 + [src/confidence.py](src/confidence.py) |
| README with setup + sample I/O | §5 + §6 above |
| AI-collaboration reflection | [REFLECTION.md](REFLECTION.md) |
