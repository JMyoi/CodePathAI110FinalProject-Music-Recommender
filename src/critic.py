import json
import os
from dataclasses import dataclass, field
from typing import Dict, List, Protocol

from src.confidence import ConfidenceResult
from src.recommender import ScoredSong, UserProfile

VERDICTS = ("strong", "ok", "weak")


@dataclass
class Recommendation:
    scored: ScoredSong
    confidence: ConfidenceResult


@dataclass
class CritiqueResult:
    verdict: str
    overall_note: str
    per_song_notes: Dict[int, str] = field(default_factory=dict)


class Critic(Protocol):
    def critique(self, user: UserProfile, recs: List[Recommendation]) -> CritiqueResult: ...


class HeuristicCritic:
    def critique(self, user: UserProfile, recs: List[Recommendation]) -> CritiqueResult:
        if not recs:
            return CritiqueResult(verdict="weak", overall_note="No recommendations were produced.")

        avg_conf = sum(r.confidence.value for r in recs) / len(recs)
        avg_coverage = sum(r.confidence.breakdown.get("coverage", 0.0) for r in recs) / len(recs)
        catalog_fit = recs[0].confidence.breakdown.get("catalog_fit", 0.0)

        if catalog_fit == 0.0:
            verdict = "weak"
            overall = (
                f"No songs in the catalog match the requested genre '{user.favorite_genre}'. "
                "These picks fell back to other features and should not be trusted."
            )
        elif avg_conf >= 0.7 and avg_coverage >= 0.75:
            verdict = "strong"
            overall = "Top picks cover most of the user's stated preferences."
        elif avg_conf >= 0.45:
            verdict = "ok"
            overall = "Reasonable picks, but coverage of the user's preferences is partial."
        else:
            verdict = "weak"
            overall = "Confidence is low — the catalog may not contain a great match for this profile."

        per_song: Dict[int, str] = {}
        for r in recs:
            cov = r.confidence.breakdown.get("coverage", 0.0)
            song_catalog_fit = r.confidence.breakdown.get("catalog_fit", 0.0)
            if song_catalog_fit == 0.0:
                per_song[r.scored.song.id] = (
                    f"Wrong genre ({r.scored.song.genre}, not {user.favorite_genre}) — "
                    "system fell back to feature similarity."
                )
            elif cov >= 0.75:
                per_song[r.scored.song.id] = "Hits most of the user's preferences."
            elif cov >= 0.5:
                per_song[r.scored.song.id] = "Partial match — a few preferences missed."
            else:
                per_song[r.scored.song.id] = "Stretch pick — limited overlap with the profile."

        return CritiqueResult(verdict=verdict, overall_note=overall, per_song_notes=per_song)


class OpenAICritic:
    def __init__(self, model: str = "gpt-4o-mini", client=None):
        self.model = model
        if client is not None:
            self.client = client
        else:
            from openai import OpenAI
            self.client = OpenAI()

    def _build_prompt(self, user: UserProfile, recs: List[Recommendation]) -> str:
        rec_lines = []
        for i, r in enumerate(recs, start=1):
            s = r.scored.song
            reasons = "; ".join(r.scored.reasons) if r.scored.reasons else "no rule-based reasons fired"
            rec_lines.append(
                f"{i}. id={s.id} '{s.title}' by {s.artist} | genre={s.genre} mood={s.mood} "
                f"energy={s.energy} acousticness={s.acousticness} | "
                f"score={r.scored.score:.2f} confidence={r.confidence.value:.2f} | reasons: {reasons}"
            )
        return (
            "You are reviewing a music recommender's top picks for a user.\n\n"
            f"User profile: favorite_genre={user.favorite_genre}, favorite_mood={user.favorite_mood}, "
            f"target_energy={user.target_energy}, likes_acoustic={user.likes_acoustic}\n\n"
            "Top picks:\n"
            + "\n".join(rec_lines)
            + "\n\nReturn a JSON object with this exact shape:\n"
              '{"verdict": "strong"|"ok"|"weak", '
              '"overall_note": "<one short sentence>", '
              '"per_song_notes": {"<song_id>": "<one short sentence>", ...}}\n'
              "Be concise. Flag any pick that looks like a stretch given the profile."
        )

    def critique(self, user: UserProfile, recs: List[Recommendation]) -> CritiqueResult:
        if not recs:
            return CritiqueResult(verdict="weak", overall_note="No recommendations were produced.")

        prompt = self._build_prompt(user, recs)
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.3,
        )
        raw = response.choices[0].message.content or "{}"
        data = json.loads(raw)

        verdict = data.get("verdict", "ok")
        if verdict not in VERDICTS:
            verdict = "ok"

        per_song_raw = data.get("per_song_notes", {}) or {}
        per_song: Dict[int, str] = {}
        for k, v in per_song_raw.items():
            try:
                per_song[int(k)] = str(v)
            except (TypeError, ValueError):
                continue

        return CritiqueResult(
            verdict=verdict,
            overall_note=str(data.get("overall_note", "")),
            per_song_notes=per_song,
        )


def make_critic() -> Critic:
    if os.environ.get("OPENAI_API_KEY"):
        try:
            return OpenAICritic()
        except Exception:
            return HeuristicCritic()
    return HeuristicCritic()
