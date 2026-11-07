from unittest.mock import MagicMock

import pytest

from app.agents import gemini

SCHEMA = {"type": "object", "properties": {"a": {"type": "integer"}}}


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake")
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    monkeypatch.setattr(gemini.time, "sleep", lambda s: None)
    gemini._cache.clear()
    yield
    gemini._cache.clear()


def _client(monkeypatch, *texts):
    client = MagicMock()
    client.models.generate_content.side_effect = [
        t if isinstance(t, Exception) else MagicMock(text=t) for t in texts
    ]
    monkeypatch.setattr(gemini, "_get_client", lambda: client)
    return client


def test_not_configured(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "")
    assert not gemini.is_configured()
    with pytest.raises(gemini.GeminiError):
        gemini.generate_json("s", "p", SCHEMA)


def test_success(monkeypatch):
    c = _client(monkeypatch, '{"a": 1}')
    assert gemini.is_configured()
    assert gemini.generate_json("s", "p", SCHEMA) == {"a": 1}
    assert c.models.generate_content.call_count == 1
    assert c.models.generate_content.call_args.kwargs["model"] == gemini.DEFAULT_MODEL


def test_retry_on_bad_json_then_success(monkeypatch):
    c = _client(monkeypatch, "not json", RuntimeError("503"), '{"a": 2}')
    assert gemini.generate_json("s", "p", SCHEMA) == {"a": 2}
    assert c.models.generate_content.call_count == 3


def test_cache_hit(monkeypatch):
    c = _client(monkeypatch, '{"a": 3}')
    assert gemini.generate_json("s", "p", SCHEMA) == {"a": 3}
    assert gemini.generate_json("s", "p", SCHEMA) == {"a": 3}
    assert c.models.generate_content.call_count == 1


def test_final_failure(monkeypatch):
    c = _client(monkeypatch, "bad", "bad", "bad")
    with pytest.raises(gemini.GeminiError):
        gemini.generate_json("s", "p", SCHEMA)
    assert c.models.generate_content.call_count == 3
