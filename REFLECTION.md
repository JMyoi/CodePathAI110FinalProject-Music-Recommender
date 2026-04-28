# Reflection — AI Collaboration and System Design

This is a reflection on how I used AI tools (specifically Claude Code) during the development of VibeFinder, what worked, what didn't, and what I'd do next.

---

## How I used AI during development

I built this project in close collaboration with Claude Code (Anthropic's CLI agent for software engineering). My workflow looked roughly like this:

1. **Framing and scoping.** I started by handing Claude the original starter (README, model_card, recommender stub) and the four extension options the assignment offered (RAG, agentic loop, bias detection, self-critique). I asked it to recommend one and lay out a plan. We negotiated the scope back and forth — I picked self-critique + confidence, OpenAI as the LLM provider, Streamlit for the UI, and a weekend-sized scope.

2. **Plan-first development.** Before any code was written, Claude wrote a detailed plan to a file and asked me to approve it. The plan listed the files to modify, the files to create, the design of each new module, the test plan, and the verification steps. I made small adjustments (adding the LLM critic toggle, asking about API keys), then approved it.

3. **Implementation.** Claude implemented the stubs in `recommender.py`, then `confidence.py`, `critic.py`, `app.py`, and the test suite — pausing periodically to run `pytest` and verify everything still passed. When tests failed (e.g. when I asked it to expand the catalog from 10 → 40 songs, the `test_load_songs_returns_full_catalog` assertion broke), it caught the failure itself and updated the test.

4. **Iteration.** I asked it to grow the catalog twice — first with fictional songs, then to swap them for real songs. Each time, Claude flagged the implications (e.g. "you'll need to re-test the metal failure-mode scenario"), did the swap, and updated everything that depended on the old data: tests, the model card's "I did not add or remove songs from the starter catalog" passage, the presentation script's talking points, the README.

5. **Documentation.** Claude wrote the model card, the architecture walk-through (`howItWorks.md`), the 5-minute presentation script, and this reflection. I treated these as drafts and edited where the framing felt off.

For the parts of the work I didn't write code for (the OpenAI prompt, the confidence weighting formula, the Streamlit layout), I read the AI's output critically before approving it — because if I couldn't explain a piece of the system, I didn't actually own it.

---

## A helpful AI suggestion

When I asked Claude to expand the catalog from 10 songs to a more realistic size, it pushed back before just doing it. It pointed out that the model card explicitly framed the small catalog as a deliberate teaching device, and that the **metal-genre failure demo** — where the user asks for a genre that isn't in the catalog and the guardrail catches it — *depends on metal not being in the catalog*. If I expanded indiscriminately and accidentally added metal, the most compelling moment in the demo would silently break.

Its suggestion was to grow the catalog *but deliberately leave out* `metal`, `k-pop`, and `trap`, and to update the model card text to reframe the limitation as "honest about *which* genres are missing" rather than "deliberately small."

That's a non-obvious tradeoff that I would not have caught on my own. The AI was working with the whole codebase in mind and noticed that an asked-for change would invalidate a downstream demo. The result is that the catalog now has 40 songs across 17 genres *and* the failure-mode demo still works — and is more convincing because the catalog isn't trivially small anymore.

---

## A flawed AI suggestion

Earlier in the project, when I asked Claude to "explore the project so you understand it," it spawned a parallel sub-agent to summarize the codebase. That sub-agent reported back that **`src/main.py` was a Streamlit UI**. It wasn't — `main.py` was a CLI runner; the Streamlit app didn't exist yet. Claude relayed this incorrect summary into its plan as if it were fact.

I caught this only because Claude itself had read `main.py` in an earlier message and the contents were still in our conversation. Claude eventually self-corrected when it actually opened the file, but for one round it was confidently planning around a wrong picture of the codebase.

The lesson: AI agents that summarize for you can confabulate, and the surface-level summary can pass the smell test if you don't already know what's in the code. The mitigation is to read at least one or two key files yourself before trusting an architecture description, especially when you're about to make a planning decision based on it.

A related flawed suggestion: when I asked for a confidence-scoring formula, the first draft used three signals weighted *equally* (0.33 each). That looked clean but it gave the **margin** signal too much power — a tiny score gap could collapse the confidence even when the song was a perfect match on every other axis. I had to push back and ask for the weights to be re-thought; the final blend (`0.5 * coverage + 0.25 * margin + 0.25 * catalog_fit`) puts coverage in the lead because "does the song actually match what the user asked for" is the most direct signal. The AI's first instinct was symmetry-for-symmetry's-sake, which felt clean but didn't serve the system's actual goals.

---

## Where my judgment overrode the AI's

A few places where I deliberately did *not* take the AI's suggestion:

- **Scope.** Claude initially proposed a 1-2 week scope with expanded data and richer features. I pulled it back to a weekend scope to keep the project demo-ready and the model card honest.
- **No vector store / RAG.** Claude pitched RAG-enriched explanations as a strong runner-up extension. For a 40-song catalog, embeddings + retrieval would have been overkill, and the self-critique loop is more pedagogically interesting. I picked the smaller, sharper extension over the more impressive-sounding one.
- **Audio feature numbers.** Claude offered to look up Spotify Audio Features API values for each real song. I declined — for a classroom demo, plausible-and-genre-appropriate is fine, and saying "these are estimates, here's where you'd get the real numbers" is more honest than pretending I had ground-truth data when I didn't.

---

## System limitations (what's still wrong with VibeFinder)

- **Tiny catalog by recommender standards.** 40 songs is enough to show the architecture; a real recommender would need thousands.
- **No artist-diversity term.** Visible in the demo: scenario 1 returns Lady Gaga twice in adjacent slots. The system has no penalty for over-representing one artist.
- **The four preference fields are a static profile.** Real listeners' tastes change by time of day, mood, activity, and social context. None of that is modeled.
- **The LLM critic can rationalize bad picks.** A model evaluating its own output is structurally biased toward agreement. The deterministic confidence is a more reliable failure detector; the LLM critic is more useful for *describing* failures than *catching* them.
- **Audio features are estimates, not measured.** The numeric values were assigned by genre/mood plausibility, not pulled from Spotify or a music-analysis library.
- **No personalization or memory.** Every session is stateless; the system can't learn from a user's actual listening behavior.

---

## Future improvements

- **Replace the heuristic audio features with Spotify Audio Features API values** for the real songs, then re-run the experiments. I expect most picks would be similar but a few outliers might shift.
- **Add a diversity term** to the scoring rule that penalizes the same artist appearing multiple times in the top-*k*. This would directly address the limitation visible in scenario 1.
- **Two-critic agreement.** Instead of one LLM critic, run two different models (e.g. gpt-4o-mini and Claude Haiku) and surface their *disagreements* as the most interesting cases. A self-evaluation loop is structurally biased; a cross-model loop has a chance of being honest.
- **Confidence calibration.** Collect a small dataset of "do you agree with this pick?" responses across ~20 user profiles, then check whether high-confidence picks really are agreed with more often than low-confidence ones. If not, the confidence formula needs to be re-weighted.
- **Lightweight learning.** Add thumbs-up / thumbs-down to the Streamlit UI, persist the feedback, and let the next round adjust the genre/mood/energy weights for that session — a tiny agentic loop that turns the static profile into a living one.
- **Better explanations.** Right now the explanation is a simple join of the rule terms. A real version would compose a sentence: "this is a strong pick for an upbeat Saturday morning, but if you're trying to focus the high energy might pull you out of it."

---

## What I learned about AI collaboration

The single biggest thing I took away is that AI tools like Claude are at their best as **collaborators on shared artifacts** — files, tests, plans — and worst when they're in a "give me a paragraph" mode. The conversational mode is fine for ideation; the file-editing mode (with verification steps and a working test suite) is where the AI actually became reliable.

The other thing I learned is that *plan-first* matters. Almost every mistake the AI made in this project was during phases where I asked it to "just do" something without writing the plan down first. Once a plan existed in a file we both could see, the AI's tendency to drift or over-engineer dropped sharply, because we both had a shared reference for what "done" meant.

Finally: an AI is great at producing the *shape* of an answer (a working scoring formula, a critic protocol, a Streamlit layout) but the *judgment* about whether the shape is right for the project — whether to use RAG vs. self-critique, whether to expand the catalog, whether to keep a critique-rationalizes-its-own-output story instead of polishing it away — has to come from me. The most valuable parts of this project (the catalog-fit guardrail, the heuristic-vs-LLM critic comparison, the missing-genre demo) all came out of judgment calls I made about *what was interesting*, not just what was easy to build.
