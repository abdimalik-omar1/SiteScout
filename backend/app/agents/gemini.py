"""Thin, thread-safe Gemini JSON helper used by the agent team."""
import hashlib
import json
import os
import threading
import time
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parents[3] / ".env")
except Exception:  # missing dotenv or .env is fine
    pass

DEFAULT_MODEL = "gemini-3.5-flash-lite"  # fast (~2 s); gemini-3.8-flash took ~50 s/call, 2.5-flash 404s for new keys
DEFAULT_TIMEOUT_S = 30  # per request; a hung call must not stall the demo
MAX_EXTRA_RETRIES = 2
BACKOFF_SECONDS = 0.5

_client = None
_client_lock = threading.Lock()
_cache: dict[str, dict] = {}
_cache_lock = threading.Lock()


class GeminiError(Exception):
    """Raised when Gemini is unavailable, unconfigured, or returns unusable output."""


def is_configured() -> bool:
    return bool(os.getenv("GEMINI_API_KEY", "").strip())


def _model() -> str:
    return os.getenv("GEMINI_MODEL", "").strip() or DEFAULT_MODEL


def _get_client():
    global _client
    with _client_lock:
        if _client is None:
            try:
                from google import genai
            except Exception as exc:
                raise GeminiError(f"google-genai SDK not available: {exc}") from exc
            from google.genai import types

            timeout_ms = int(float(os.getenv("GEMINI_TIMEOUT_S", "") or DEFAULT_TIMEOUT_S) * 1000)
            _client = genai.Client(
                api_key=os.getenv("GEMINI_API_KEY"),
                http_options=types.HttpOptions(timeout=timeout_ms),
            )
        return _client


def _call(client, model: str, system: str, prompt: str, schema: dict) -> str:
    try:
        from google.genai import types
    except Exception as exc:
        raise GeminiError(f"google-genai SDK not available: {exc}") from exc
    config = types.GenerateContentConfig(
        system_instruction=system,
        response_mime_type="application/json",
        response_schema=schema,
        temperature=0.2,
    )
    resp = client.models.generate_content(model=model, contents=prompt, config=config)
    return resp.text


def generate_json(system: str, prompt: str, schema: dict) -> dict:
    if not is_configured():
        raise GeminiError("GEMINI_API_KEY is not set")
    model = _model()
    key = hashlib.sha256(
        json.dumps([model, system, prompt, json.dumps(schema, sort_keys=True)]).encode()
    ).hexdigest()
    with _cache_lock:
        if key in _cache:
            return json.loads(json.dumps(_cache[key]))

    client = _get_client()
    last_exc: Exception | None = None
    for attempt in range(MAX_EXTRA_RETRIES + 1):
        if attempt:
            time.sleep(BACKOFF_SECONDS * attempt)
        try:
            text = _call(client, model, system, prompt, schema)
            data = json.loads(text)
            if not isinstance(data, dict):
                raise ValueError("response JSON is not an object")
        except GeminiError:
            raise
        except Exception as exc:
            last_exc = exc
            code = getattr(exc, "code", None)
            if isinstance(code, int) and 400 <= code < 500 and code != 429:
                break  # bad model/key/request: retrying cannot help
            continue
        with _cache_lock:
            _cache[key] = data
        return json.loads(json.dumps(data))
    raise GeminiError(f"Gemini call failed after retries: {last_exc}") from last_exc
