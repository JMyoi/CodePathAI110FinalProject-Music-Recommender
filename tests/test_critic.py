import json
from types import SimpleNamespace
from unittest.mock import MagicMock

from src.confidence import ConfidenceResult
from src.critic import (
    HeuristicCritic,
    OpenAICritic,
    Recommendation,
    make_critic,
)
from src.recommender import Recommender, ScoredSong, Song, UserProfile


def _user():
    return UserProfile(favorite_genre="pop", favorite_mood="happy",
                       target_energy=0.8, likes_acoustic=False)


def _song():
    return Song(id=1, title="Pop Track", artist="A", genre="pop", mood="happy",
                energy=0.8, tempo_bpm=120, valence=0.9, danceability=0.8, acousticness=0.2)


def _rec(score=2.5, conf=0.85, coverage=0.8, catalog_fit=0.5):
    return Recommendation(
        scored=ScoredSong(song=_song(), score=score, reasons=["matches genre", "matches mood"]),
        confidence=ConfidenceResult(
            value=conf,
            breakdown={"coverage": coverage, "margin": 0.5, "catalog_fit": catalog_fit},
        ),
    )


def test_heuristic_critic_returns_valid_shape():
    critic = HeuristicCritic()
    result = critic.critique(_user(), [_rec(), _rec(score=1.5, conf=0.6, coverage=0.5)])
    assert result.verdict in {"strong", "ok", "weak"}
    assert isinstance(result.overall_note, str) and result.overall_note
    assert 1 in result.per_song_notes


def test_heuristic_critic_calls_out_missing_catalog_fit():
    critic = HeuristicCritic()
    result = critic.critique(_user(), [_rec(coverage=0.25, catalog_fit=0.0, conf=0.2)])
    assert result.verdict == "weak"
    assert "catalog" in result.overall_note.lower() or "match" in result.overall_note.lower()


def test_heuristic_critic_strong_verdict_for_high_coverage():
    critic = HeuristicCritic()
    result = critic.critique(_user(), [_rec(coverage=1.0, conf=0.9, catalog_fit=1.0),
                                       _rec(coverage=0.75, conf=0.75, catalog_fit=1.0)])
    assert result.verdict == "strong"


def test_openai_critic_with_mocked_client():
    fake_client = MagicMock()
    fake_response = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps({
            "verdict": "strong",
            "overall_note": "Solid picks for an upbeat pop listener.",
            "per_song_notes": {"1": "Great match for the profile."},
        })))]
    )
    fake_client.chat.completions.create.return_value = fake_response

    critic = OpenAICritic(client=fake_client)
    result = critic.critique(_user(), [_rec()])

    assert result.verdict == "strong"
    assert result.per_song_notes[1] == "Great match for the profile."
    fake_client.chat.completions.create.assert_called_once()
    call_kwargs = fake_client.chat.completions.create.call_args.kwargs
    assert call_kwargs["response_format"] == {"type": "json_object"}


def test_openai_critic_normalizes_unknown_verdict():
    fake_client = MagicMock()
    fake_client.chat.completions.create.return_value = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps({
            "verdict": "amazing",
            "overall_note": "n/a",
            "per_song_notes": {},
        })))]
    )
    critic = OpenAICritic(client=fake_client)
    result = critic.critique(_user(), [_rec()])
    assert result.verdict == "ok"


def test_make_critic_returns_heuristic_when_no_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    critic = make_critic()
    assert isinstance(critic, HeuristicCritic)


def test_critic_handles_empty_recs():
    critic = HeuristicCritic()
    result = critic.critique(_user(), [])
    assert result.verdict == "weak"
