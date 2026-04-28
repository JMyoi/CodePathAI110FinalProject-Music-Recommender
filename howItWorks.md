# How VibeFinder Works

A walk-through of the codebase: what each file does, how data flows through the system, and the key types and functions you'd want to be able to point at if a grader asks.

---

## Big picture

VibeFinder is three layers stacked on top of a small CSV:

```
        data/songs.csv  (40 rows)
               │
               ▼
   ┌───────────────────────────┐
   │  Layer 1: Scoring          │   src/recommender.py
   │  rule-based, deterministic │
   └───────────────────────────┘
               │  produces ranked list of (song, score, reasons)
               ▼
   ┌───────────────────────────┐
   │  Layer 2: Confidence       │   src/confidence.py
   │  derives 0–1 trust value   │
   │  from coverage/margin/fit  │
   └───────────────────────────┘
               │  produces (song, score, reasons, confidence) per pick
               ▼
   ┌───────────────────────────┐
   │  Layer 3: Self-critique    │   src/critic.py
   │  reviews the whole top-k   │
   │  Heuristic OR LLM critic   │
   └───────────────────────────┘
               │  produces verdict + per-song notes
               ▼
       CLI (src/main.py)  /  Streamlit UI (src/app.py)
```

Each layer adds *meta-information*. The scorer says "here are the picks." The confidence layer says "here's how much you should trust each one." The critic says "here's a sanity check on the whole batch." The point of the project is to study what happens when you ask a system not just to recommend but to police itself.

---

## End-to-end data flow

Tracing what happens when a user runs `python -m src.main`:

1. **Load.** [src/main.py](src/main.py) calls [`load_songs("data/songs.csv")`](src/recommender.py) → returns a `list[Song]`.
2. **Build user profile.** A `UserProfile` dataclass is constructed from the user's preferences (in the CLI it's hard-coded; in the Streamlit app it comes from sidebar widgets).
3. **Score & rank.** A `Recommender(songs)` is instantiated; `recommender.score_all(user)` returns a `list[ScoredSong]` sorted by score descending. The top *k* is sliced off.
4. **Compute confidence.** For each picked song, [`compute_confidence(user, song, all_songs, ranked)`](src/confidence.py) returns a `ConfidenceResult` (a 0–1 value plus a breakdown dict).
5. **Wrap into Recommendations.** Each `(ScoredSong, ConfidenceResult)` pair becomes a `Recommendation` — the unit the critic operates on.
6. **Critique.** [`make_critic()`](src/critic.py) returns either an `OpenAICritic` (if `OPENAI_API_KEY` is set) or a `HeuristicCritic`. `critic.critique(user, recs)` returns a `CritiqueResult` with an overall verdict and per-song notes.
7. **Render.** The CLI prints; the Streamlit app renders cards with progress bars.

The Streamlit app ([src/app.py](src/app.py)) follows the same flow but the user profile is built from sidebar widgets and recomputation happens reactively whenever a widget changes.

---

## File-by-file

### [src/__init__.py](src/__init__.py)

Empty file. Its only job is to mark `src/` as a Python package so `from src.recommender import ...` works in tests and in the Streamlit app. Without it, the imports break depending on which directory you launch from.

### [src/recommender.py](src/recommender.py) — Layer 1: scoring

The base recommender. Three dataclasses and one main class.

**Dataclasses:**

- `Song` — one row of the CSV. Has the descriptive fields (`id`, `title`, `artist`, `genre`, `mood`) and the four numeric audio features (`energy`, `tempo_bpm`, `valence`, `danceability`, `acousticness`).
- `UserProfile` — what the user wants. Four fields: `favorite_genre`, `favorite_mood`, `target_energy`, `likes_acoustic`.
- `ScoredSong` — a `Song` with a `score: float` and a `reasons: list[str]` attached. The reasons are human-readable strings that say which scoring terms fired, used later by `explain_recommendation`.

**The `Recommender` class:**

```python
class Recommender:
    def __init__(self, songs: list[Song])
    def _score(self, user, song) -> tuple[float, list[str]]   # the rule
    def score_all(self, user) -> list[ScoredSong]              # rank everything
    def recommend(self, user, k=5) -> list[Song]               # top-k songs
    def recommend_scored(self, user, k=5) -> list[ScoredSong]  # top-k with scores
    def explain_recommendation(self, user, song) -> str        # human prose
```

The most important method is `_score(user, song)`. It applies four additive rules:

| Rule                              | Contribution                                  |
|-----------------------------------|-----------------------------------------------|
| Genre match                       | `+2.0`                                        |
| Mood match                        | `+1.5`                                        |
| Energy fit                        | `-abs(song.energy - user.target_energy)`      |
| Acoustic alignment                | `±0.5` if `acousticness > 0.6`                |

It returns the score *and* a list of reason strings — this is the trick that lets `explain_recommendation` be honest (it only mentions terms that actually fired).

**Functional helpers** (`load_songs`, `score_song`, `recommend_songs`) exist because the original starter API was function-based with `dict` parameters. Rather than have two parallel implementations, the helpers wrap the OOP `Recommender` class. So `recommend_songs(user_prefs, songs, k)` internally builds a `UserProfile` and a `Recommender` and delegates. This is why both `python -m src.main` (uses the OOP API) and the original starter tests (used the dict-based API) keep working from a single source of truth.

### [src/confidence.py](src/confidence.py) — Layer 2: how much to trust each pick

A small module: one dataclass and one public function.

**`ConfidenceResult`:**

```python
@dataclass
class ConfidenceResult:
    value: float                  # final 0–1 confidence
    breakdown: dict[str, float]   # {"coverage": ..., "margin": ..., "catalog_fit": ...}
```

The `breakdown` is what powers the UI's "why is this confidence what it is" expander.

**`compute_confidence(user, song, all_songs, ranked)`** is the only function callers use. Internally it calls three private helpers:

- `_coverage(user, song)` → fraction of the four user preferences this song hits (genre, mood, energy bucket within ±0.2, acoustic alignment). Range 0.0–1.0.
- `_margin(rank, ranked)` → score gap to the next-ranked song, capped at 1.0. Big gap = confident; ties = unsure.
- `_catalog_fit(user, all_songs)` → `min(1.0, num_genre_matches / 3.0)`. If the user's favorite genre doesn't appear in the catalog at all, this collapses to 0.0 — and the final confidence with it.

The final value is a weighted blend:

```python
value = 0.5 * coverage + 0.25 * margin + 0.25 * catalog_fit
```

Coverage gets the most weight because "does this song actually match what you asked for" is the most direct signal. Catalog-fit is the term that catches the **metal-genre failure mode** — when no song matches the user's genre, every confidence in the top-k drops, regardless of score.

### [src/critic.py](src/critic.py) — Layer 3: self-critique

The most interesting file in the project. Defines a pluggable interface for critics, two implementations, and a factory.

**Types:**

```python
@dataclass
class Recommendation:
    scored: ScoredSong
    confidence: ConfidenceResult

@dataclass
class CritiqueResult:
    verdict: str                    # "strong" | "ok" | "weak"
    overall_note: str
    per_song_notes: dict[int, str]  # keyed by song.id

class Critic(Protocol):
    def critique(self, user: UserProfile, recs: list[Recommendation]) -> CritiqueResult: ...
```

`Critic` is a `typing.Protocol`. Anything with a `critique(user, recs) -> CritiqueResult` method satisfies it. This is what lets the LLM and heuristic critics be swapped in and out without changing the code that uses them — including the tests, which use mock objects against the same protocol.

**`HeuristicCritic`** — derives a `CritiqueResult` from the confidence breakdowns alone. No LLM, no API calls, no network. Logic:

- If the first pick's `catalog_fit == 0.0` → verdict is `weak` and the note explicitly calls out the missing genre.
- Otherwise it averages the confidence values and coverages and emits `strong` / `ok` / `weak` based on thresholds.
- Per-song notes come from each song's coverage value (≥0.75 → "hits most preferences"; ≥0.5 → "partial match"; otherwise → "stretch pick").

This is the deterministic critic. It's harsh but correct. It's what runs when there's no API key, and it's what the tests run against because it's reproducible.

**`OpenAICritic`** — calls `gpt-4o-mini` via the `openai` SDK.

The interesting bits:

```python
def __init__(self, model="gpt-4o-mini", client=None):
    self.client = client if client is not None else OpenAI()
```

The optional `client` parameter is there for testing. Production code doesn't pass one and gets a real `OpenAI()` client; tests pass a `MagicMock()` so they can assert on what got sent without hitting the API.

`_build_prompt(user, recs)` constructs a single prompt that includes the user profile, every top-pick with its score and reasons, and instructions to return a structured JSON object with `verdict`, `overall_note`, and `per_song_notes`.

`critique(user, recs)` then calls:

```python
response = self.client.chat.completions.create(
    model=self.model,
    messages=[{"role": "user", "content": prompt}],
    response_format={"type": "json_object"},
    temperature=0.3,
)
```

The `response_format={"type": "json_object"}` is **OpenAI's JSON mode** — it forces the model to return valid JSON, removing the need for hairy parsing. After the response comes back, `critique` parses it with `json.loads`, normalizes the verdict (any unknown verdict becomes `"ok"`), coerces the per-song-note keys to `int`, and returns a `CritiqueResult`.

Low temperature (0.3) is intentional — the critic should be consistent, not creative.

**`make_critic()`** is the factory. It checks `os.environ["OPENAI_API_KEY"]`. If set, it tries to build an `OpenAICritic`; if anything fails (e.g. SDK not installed), it falls back to `HeuristicCritic`. If unset, it returns `HeuristicCritic` directly. This means the demo, the tests, and `python -m src.main` all work without a key — the LLM is a strict upgrade, never a hard dependency.

### [src/main.py](src/main.py) — the CLI runner

Forty lines. Loads songs, builds a hard-coded `UserProfile` for the `pop / happy / 0.8 / not acoustic` user, runs the full three-layer pipeline, and prints the results. Useful for grading and debugging — runs end-to-end in under a second.

The interesting line is:

```python
critic = make_critic()
critique = critic.critique(user, recs)
```

This is the same line that runs in the Streamlit app. The factory abstracts away the LLM/heuristic decision so the rest of the code doesn't care.

### [src/app.py](src/app.py) — the Streamlit UI

The demo surface. Same pipeline as `main.py` but interactive. Highlights:

- **`@st.cache_data`** on `load_songs` so the CSV isn't re-read on every widget interaction.
- **Sidebar** builds the `UserProfile` from widgets: a genre dropdown (with a `(custom)` option that reveals a text input for stress-testing absent genres), a mood dropdown, an energy slider, an acoustic checkbox, and a *k* slider.
- **LLM-critic toggle** that auto-disables itself if no `OPENAI_API_KEY` is found, with a caption explaining why. Toggling it swaps `OpenAICritic` for `HeuristicCritic` at request time — that's why the toggle is instant.
- **Per-song cards** rendered with `st.container(border=True)`, showing title/artist, the rule-based explanation, the critic's per-song note, the score as a metric, and the confidence as a `st.progress` bar with the breakdown in an expander.
- **Verdict pill** at the bottom — a small colored badge (`green` for strong, `yellow` for ok, `red` for weak) followed by the critic's overall sentence.

The first six lines of `app.py` add the project root to `sys.path`. This is needed because `streamlit run src/app.py` doesn't run the file as part of the `src` package — without the path manipulation, `from src.recommender import ...` would fail.

---

## Key types and how they relate

```
   UserProfile ────────┐
                       │
        Song ──────► Recommender._score ──► (float, list[str])
                       │
                       ▼
                  ScoredSong ────────────► explain_recommendation
                       │
                       ▼
                ConfidenceResult ─────► coverage / margin / catalog_fit
                       │
                       ▼
                Recommendation ─────────► Critic.critique
                       │
                       ▼
                CritiqueResult
                       │
                       ▼
                CLI / Streamlit
```

Every type is a `@dataclass` (or a `Protocol`, in the case of `Critic`). Dataclasses are used here because:

- They give you `__init__`, `__repr__`, and equality for free.
- They print nicely in test output.
- They're transparent — no hidden state, no magic.

If you had to pick the **one** function in the whole project to point at, it's `Recommender._score`. Everything downstream — the explanation, the confidence breakdown, the critic's prompt — is derived from the score and the reasons it produced. Get that function right and the rest follows.

---

## Why this design

A few choices worth being able to defend:

**Why a separate confidence module instead of just adding it to `Recommender`?**
Because confidence depends on *all* the songs and the full ranked list, not just the song being scored. Putting it in `_score` would have made `_score` know about ranking, which it shouldn't.

**Why a `Critic` protocol with two implementations?**
So the demo runs offline (no API key required), the tests stay deterministic, and the LLM critic and heuristic critic can be compared apples-to-apples — which turned out to be the most interesting result of the project.

**Why dataclasses everywhere instead of dicts?**
Two reasons. One: type hints catch mistakes at write-time (you'd notice immediately if you tried to access `song.titel`). Two: the existing starter test imported `Song`, `UserProfile`, and `Recommender` by name — keeping those classes preserves backward compatibility with the original `tests/test_recommender.py`.

**Why is the OpenAI client injectable via the constructor?**
Pure testability. `OpenAICritic(client=MagicMock())` lets `tests/test_critic.py` assert on the exact prompt and response handling without hitting the network or needing an API key in CI.

---

## What to read in what order

If someone hands you this codebase cold:

1. [data/songs.csv](data/songs.csv) — see the data first
2. [src/recommender.py](src/recommender.py) — `Song`, `UserProfile`, `Recommender._score`
3. [src/confidence.py](src/confidence.py) — `compute_confidence`
4. [src/critic.py](src/critic.py) — start with `HeuristicCritic`, then `OpenAICritic`
5. [src/main.py](src/main.py) — see the pipeline assembled
6. [src/app.py](src/app.py) — see the UI
7. [tests/](tests/) — the contract everything has to honor
