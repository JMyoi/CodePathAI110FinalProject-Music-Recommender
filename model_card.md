# 🎧 Model Card: VibeFinder 1.0

## 1. Model Name

**VibeFinder 1.0** — a content-based music recommender with confidence scoring and an LLM self-critique loop.

---

## 2. Intended Use

VibeFinder suggests up to 10 songs from a 40-song classroom catalog based on a user-provided taste profile (favorite genre, favorite mood, target energy, acoustic preference). It is for AI110 classroom exploration — specifically for studying how a recommender can self-evaluate, and where that self-evaluation breaks down. **Not** intended for real users or production music products.

It assumes the user can articulate their taste in those four fields. It does not handle implicit feedback, listening history, or social context.

---

## 3. How the Model Works

For each song in the catalog, VibeFinder computes a score by adding bonuses for matching the user's favorite genre and mood, subtracting a penalty proportional to the gap between the song's energy and the user's target energy, and applying a small bonus or penalty for acoustic alignment. The top *k* songs are returned, sorted by score.

Each pick also gets a **confidence value** between 0 and 1. Confidence blends three signals: how many of the user's preferences this song actually matches (coverage), how big a lead this song has over the next-ranked song (margin), and how well-represented the user's favorite genre is in the catalog at all (catalog fit). A song can have a high score and still have low confidence — for example, if it is the only song in a requested genre and the catalog has few alternatives.

After the top *k* is picked, a **critic** reviews the whole batch and returns a verdict (`strong` / `ok` / `weak`), an overall note, and a one-line note per song. The LLM critic (`gpt-4o-mini`) gets the user profile and the picks; the heuristic critic (used when no API key is set) derives the same output shape from the confidence breakdowns.

The change from the starter logic is the addition of the confidence layer and the critic loop. The starter only produced ranked picks; VibeFinder also produces *meta-information about the picks*.

---

## 4. Data

The dataset is `data/songs.csv`, which contains **40 songs across 17 genres** with the columns: `id, title, artist, genre, mood, energy, tempo_bpm, valence, danceability, acousticness`. Genres represented: pop, lofi, rock, ambient, jazz, synthwave, indie pop, hip-hop, r&b, electronic, folk, indie rock, country, classical, blues, reggae, soul. Moods: happy, chill, intense, relaxed, moody, focused, melancholy, romantic, nostalgic, energetic.

I expanded the original 10-song starter catalog to 40 songs to broaden genre coverage, but **deliberately left out metal, k-pop, and trap** so the catalog-fit failure mode is still demonstrable. This is the most honest version of the limitation the original starter was illustrating: even a "diverse" catalog will always exclude *something*, and the system needs to be honest about it rather than confidently recommending whatever is closest.

Whose taste does this reflect? It's curated to span a typical young-adult Western pop landscape — chill/study moods, upbeat dance/party axes, and a few "thoughtful" genres (folk, classical, jazz). Despite the expansion, many cultural and global musics are still missing — no Latin, no K-pop, no Afrobeat, no Indian classical, no traditional regional music, no extreme metal subgenres. The bias is smaller than in the starter, but it isn't gone.

---

## 5. Strengths

- **Honest about its limits.** When a user requests a genre that doesn't exist in the catalog, confidence drops visibly and the critic flags the picks as `weak`. This is the strongest behavior in the system.
- **Transparent scoring.** The rule-based scorer makes it easy to explain why each song was picked. There is no black box at the recommendation step.
- **Pluggable critic.** The same `Critic` interface supports the LLM and the heuristic, so the demo runs offline and the LLM is a strict upgrade rather than a dependency.
- **High-coverage profiles get visibly confident picks.** A user asking for `pop / happy / 0.8 energy / not acoustic` gets *Sunrise City* as the top pick with confidence ≈ 0.87 — and the breakdown shows why.

---

## 6. Limitations and Bias

- **Limited catalog.** Forty songs across seventeen genres is broader than the starter, but still small enough that some genres only have one or two songs. The catalog-fit term still does real work, and a real version would need thousands of songs and finer-grained sub-genres before this concern faded.
- **Genre coverage is still biased.** Western pop, lofi, and electronic-adjacent moods dominate the catalog. Metal, k-pop, and trap were deliberately excluded to preserve the catalog-fit failure demo, but global and traditional musics are also missing — that's not a deliberate teaching choice, it's the actual bias. Users whose taste sits outside the catalog get penalized through no fault of their own.
- **The four preference fields treat all users as having the same taste shape.** A real listener's preferences vary by time of day, activity, and mood — VibeFinder collapses all of that into a single static profile.
- **The LLM critic can rationalize bad picks.** Self-evaluation by the same kind of model that produced the explanation is structurally biased toward agreement. The heuristic critic is harsher and more reliable on the catalog-fit failure mode, even though it has no language understanding.
- **No fairness metric for artist diversity.** If an artist appears multiple times in the catalog, the recommender has no penalty for putting all of their songs in the top *k*. A real product would need a diversity term.

In a real product, these biases would translate to "VibeFinder is great for users whose taste matches the curator's, and quietly worse for everyone else."

---

## 7. Evaluation

I evaluated VibeFinder in three ways:

1. **Unit tests** (`tests/`) — 19 tests covering scoring, loading, confidence bounds, critic shape, the LLM JSON parser (with a mocked client), and several negative cases (missing genre, low coverage).
2. **Profile sweeps** — I tried five user profiles (pop/happy/high-energy, lofi/chill/low-energy, jazz/relaxed/medium, ambient/chill/very-low, and the deliberately-broken metal/intense profile) and compared the critic's verdict against my own intuition for whether the picks were sensible.
3. **Critic comparison** — for each profile, I ran with and without `OPENAI_API_KEY` set. The interesting finding: on the `metal` profile, both critics return `weak` — but the heuristic critic does it because catalog-fit is 0, while the LLM critic does it via reasoning. On the `pop` profile, both return `ok` or `strong`. The most divergent case was the `jazz` profile, where the LLM gave a more nuanced "ok with caveats" while the heuristic just said "ok".

What surprised me: the *deterministic* confidence signal caught failures more reliably than the LLM critic did. The LLM is better at *describing* why a pick is weak; the heuristic is better at *detecting* it.

---

## 8. Future Work

- **Expand the catalog further** to ~500+ songs with sub-genres (e.g. "indie pop" → "dream pop", "bedroom pop") and revisit whether the catalog-fit term still does useful work at that scale or becomes noise.
- **Diversity term** — penalize the score when the same artist appears multiple times in the top *k*.
- **Iterate with feedback** — let the user thumbs-up / thumbs-down a pick, and use that to adjust the weights for the next round (a tiny agentic loop).
- **Compare two critics on the same picks** and surface disagreements as the most interesting cases for the user to look at.
- **Confidence calibration** — collect a small dataset of "do you agree with this pick?" responses and check whether high-confidence picks really are agreed with more often than low-confidence ones.

---

## 9. Personal Reflection

The biggest thing I took away from building this is that *making a prediction* and *knowing how much to trust the prediction* are very different problems, and the second is the more interesting one. The scoring rule was straightforward — a few additions and a subtraction. The confidence layer made me actually think about what could go wrong: ties, missing genres, profiles the catalog can't serve.

I was also surprised by how often the LLM critic agreed with weak picks. It's a small reminder that an AI evaluating its own work is structurally biased — the same patterns that produced a confident wrong answer are still there when the same model is asked to grade it. For a real recommender like Spotify or YouTube, I now think the most important question isn't "what's the best recommendation," it's "when should the system *decline* to recommend at all?" — and the answer to that has to come from something other than the model's own confidence.
