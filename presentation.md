# VibeFinder — 5-Minute Presentation Notes

Times are speaking-time targets. Say less than this if you talk fast, never more.

---

## 0:00–0:30 — Hook & framing (30s)

Open with the framing, not the build. The build is boring; the framing is the hook.

> "I built a music recommender — but the part I want to talk about isn't *what* it recommends. It's whether it knows when *not to trust itself*. That turns out to be a way more interesting problem."

Then say what it is in one sentence:

> "VibeFinder takes a user's taste profile, scores songs from a small catalog, and then has an AI critic review its own picks — flagging the ones that look like a stretch."

---

## 0:30–1:15 — The three layers (45s)

Walk through them quickly. **Don't read code.** Just name each layer and what it does.

1. **Scoring** — rule-based. Genre match, mood match, energy distance, acoustic preference. Transparent, no black box.
2. **Confidence** — a 0–1 number per pick. Three signals: *coverage* (how many of your prefs this song hits), *margin* (how much it beats the next song), and *catalog fit* (does the catalog even contain your genre).
3. **Self-critique** — after the top 5 are picked, an LLM (gpt-4o-mini) reviews the whole batch and returns a verdict: strong, ok, or weak. There's also a deterministic fallback critic for when there's no API key.

> "The whole point of the extension is that the system produces meta-information about its own output, not just the output."

---

## 1:15–3:15 — Live demo (2 minutes — the heart of the talk)

python -m src.demo 

Talk through the three scenarios as the output appears (this hits rubric items 4, 5, and gives you the "AI feature behavior" + "clear outputs for each case" beats from the [IMPORTANT] block).

Open `python -m streamlit run src/app.py` and narrate as you click. Three runs:

### Run 1 — happy path + the artist-diversity moment (~50s)

Profile: `pop / happy / 0.8 energy / not acoustic`. Top pick: **Whitney Houston — *I Wanna Dance with Somebody***. Confidence ~0.94, verdict **strong**.

> "This is the easy case. The catalog has a song that hits every preference — pop, happy, high energy. Confidence 0.94, the critic says strong."

Then **point at slots 2 and 3**: *Born This Way* and *Bad Romance* — both Lady Gaga.

> "But look at numbers two and three. Both Lady Gaga. The recommender has no penalty for picking the same artist twice in a row. That's a real failure mode in real recommenders — and it's showing up immediately in a 40-song catalog. Worth holding onto, because it's the kind of thing the critic *should* catch but doesn't."

### Run 2 — the failure mode (~45s)

Switch genre to **`metal`** (custom — deliberately not in the catalog). Top picks: **Green Day's *Holiday*, Guns N' Roses's *Welcome to the Jungle*, Daft Punk's *Harder Better Faster Stronger***. **Point at the catalog-fit term collapsing to 0.00**.

> "Watch what happens. The catalog has 40 songs across 17 genres — but no metal. The system *still* returns picks — it has to, that's what it was asked to do. It serves up Green Day, Guns N' Roses, Daft Punk: all high-energy, all intense. But every confidence breakdown shows catalog-fit at zero, and the critic flags the whole batch as weak. None of those is actually metal. The system is being honest about a failure that the score alone wouldn't reveal."

**This is your money shot.** Spend a beat on it.

### Run 3 — toggle the LLM critic off (~30s)

Same profile, flip "Use LLM critic" off.

> "And this still works without an API key — the heuristic critic catches the same failure from the confidence breakdown. The LLM is nicer language, but the deterministic signal is what's actually doing the work."

---

## 3:15–4:00 — The interesting finding (45s)

This is your "what I learned" moment. Don't skip it — it's what separates this from "I built a recommender."

> "The thing that surprised me most: the deterministic confidence catches failures *more reliably* than the LLM critic does. The LLM is great at *describing* why a pick is weak. The math is what *detects* it. When I asked the LLM to grade picks it had effectively produced, it would sometimes rationalize them — which makes sense, because a model evaluating its own output is structurally biased toward agreement.
>
> That changed how I think about real recommenders. The most important question isn't 'what's the best recommendation' — it's 'when should the system decline to recommend at all,' and the model can't answer that question about itself."

---

## 4:00–4:30 — Limitations (30s)

Be honest. Graders love this.

> "Three limitations worth flagging. One: the catalog has 40 songs across 17 genres — broader than the starter, but real recommenders work on millions, so the catalog-fit term wouldn't necessarily transfer. Two: the four preference fields treat all users as having the same taste shape, which collapses real listening behavior into a static profile. Three: even with 40 songs, the catalog skews toward Western pop and chill genres — global and traditional musics are absent. The system is honest about it via the catalog-fit term, but the bias is still there."

---

## 4:30–5:00 — Wrap (30s)

> "So that's VibeFinder. It's a small system but the lesson generalizes: building an AI that *knows what it doesn't know* is a different kind of work than building one that produces an answer. The recommender was the easy part. The confidence layer is the part I'd want in any real product."

---

## Things to NOT do

- Don't show code on screen unless someone asks. Code in slides kills the energy.
- Don't read the model card aloud. Refer to it for the writeup but the talk is about the demo.
- Don't say "the LLM critic is better." It's not, and your finding is the opposite — own that.
- Don't apologize for the small catalog. Frame it as deliberate ("the catalog is small *on purpose* — it lets me show the failure mode").

---

## What to have ready before you start

- Streamlit already running in a browser tab (don't open it cold during the talk)
- The pop/happy profile pre-loaded so the Whitney Houston pick is the first thing on screen
- The metal-genre demo pre-tested so you know it produces "weak"
- One slide max, with the three layers (scoring / confidence / critic) as a diagram or three boxes
- A one-line answer ready for "did you use the API?" → "Yes, gpt-4o-mini, but the heuristic fallback works without it — that's part of the design."
- A one-line answer ready for "where did the audio features come from?" → "Tempos are accurate from public song data; energy/valence/danceability/acousticness are reasonable estimates. Spotify's Audio Features API would give exact numbers if I needed them."

---

## Likely Q&A

**"Why a heuristic fallback if the LLM is the point?"**
> "Two reasons. One, the demo has to work without internet or an API key. Two, building both let me compare them — and the comparison was the most interesting finding."

**"How much did the API cost?"**
> "About a hundredth of a cent per call. The whole project ran on under a dollar."

**"Could the LLM critic be improved?"**
> "Yes — give it the *full catalog* instead of just the top picks, so it can suggest what's missing. Or have two different models critique each other instead of one model critiquing itself."

**"What would you do with a bigger catalog?"**
> "Add a diversity term so the same artist doesn't dominate the top-k, and revisit whether catalog-fit still does useful work or becomes noise."

**"Did you collect the audio feature data yourself?"**
> "BPMs are publicly known for famous songs. The other four features — energy, valence, danceability, acousticness — are reasonable estimates I assigned per genre and mood. Spotify publishes exact values via their Audio Features API; for a classroom demo I went with plausible-and-genre-appropriate. The system's behavior, not the exact data, is what I'm demonstrating."

---

## Run commands (cheat sheet)

```bash
pip install -r requirements.txt    # gets the new deps
pytest                             # 20 tests
python -m src.main                 # CLI
python -m streamlit run src/app.py           # UI
```
