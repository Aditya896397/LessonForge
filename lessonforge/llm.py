"""Thin wrapper around the Google Gen AI SDK (Gemini).

Two call styles are used by the pipeline:

* ``grounded()``: free-text generation with the Google Search tool turned on.
  Returns the text plus the web pages Gemini actually used (grounding metadata).
  This is what makes research and fact checking evidence-based rather than
  "from the model's memory".
* ``structured()``: JSON output validated against a Pydantic schema.

Gemini does not allow the search tool and a JSON response schema in the same
call, which is why research/verification and structuring are separate calls.

All calls go through ``_with_retries`` (exponential backoff on rate limits,
5xx errors and timeouts) and raise ``LLMError`` with a readable message on
failure, so the UI can show it and offer a retry.
"""
from __future__ import annotations

import json
import logging
import random
import re
import time
from dataclasses import dataclass, field
from typing import Callable, Protocol, TypeVar

from pydantic import BaseModel, ValidationError

from .config import Settings

log = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)


class LLMError(RuntimeError):
    """Raised when a model call fails after retries (message is user-facing)."""


class DailyQuotaError(LLMError):
    """The free-tier daily request quota for one model is used up (retrying won't help today)."""


def is_daily_quota(exc: Exception) -> bool:
    s = str(exc)
    return "PerDay" in s or "per day" in s.lower()


class InvalidJSONError(RuntimeError):
    """Model output did not match the schema; worth retrying with a fresh sample."""


@dataclass
class GroundedResult:
    text: str
    sources: list[dict] = field(default_factory=list)  # [{"title", "uri"}] (uri may be a redirect)
    queries: list[str] = field(default_factory=list)
    supports: list[dict] = field(default_factory=list)  # [{"text", "source_indices"}]


class LLMClient(Protocol):
    def grounded(self, prompt: str, system: str, model: str | None = None,
                 temperature: float = 0.2, retries: int | None = None) -> GroundedResult: ...

    def structured(self, prompt: str, schema: type[T], system: str, model: str | None = None,
                   temperature: float = 0.3) -> T: ...

    def generate(self, prompt: str, system: str, model: str | None = None,
                 temperature: float = 0.3) -> str: ...


# --------------------------------------------------------------------------- #
# Helpers (pure functions, unit tested)
# --------------------------------------------------------------------------- #
_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)


def extract_json(text: str) -> str:
    """Pull the first JSON object/array out of a model response."""
    if not text:
        raise ValueError("empty response")
    m = _FENCE_RE.search(text)
    candidate = m.group(1).strip() if m else text.strip()
    if candidate[:1] in "{[":
        return candidate
    # fall back to the outermost {...}
    start, end = candidate.find("{"), candidate.rfind("}")
    if start != -1 and end > start:
        return candidate[start:end + 1]
    raise ValueError("no JSON object found in response")


def parse_model(text: str, schema: type[T]) -> T:
    raw = extract_json(text)
    try:
        return schema.model_validate_json(raw)
    except ValidationError:
        # tolerate trailing commas, a common LLM slip
        cleaned = re.sub(r",\s*([}\]])", r"\1", raw)
        return schema.model_validate(json.loads(cleaned))


def _is_retryable(exc: Exception) -> bool:
    if isinstance(exc, InvalidJSONError):
        return True
    msg = f"{type(exc).__name__} {exc}".lower()
    code = getattr(exc, "code", None) or getattr(exc, "status_code", None)
    if isinstance(code, int) and (code == 429 or code >= 500):
        return True
    return any(k in msg for k in ("429", "resource_exhausted", "rate", "quota", "503", "500",
                                   "unavailable", "overloaded", "timeout", "timed out",
                                   "deadline", "connection", "internal"))


def _friendly(exc: Exception) -> str:
    msg = str(exc)
    low = msg.lower()
    if "api key" in low or "api_key" in low or "permission_denied" in low or "401" in low:
        return "Gemini rejected the API key. Check GEMINI_API_KEY in your .env file."
    if "not found" in low and "model" in low:
        return f"The configured Gemini model was not found ({msg[:200]}). Set GEMINI_MODEL to an available model."
    if isinstance(exc, InvalidJSONError):
        return f"Gemini kept returning malformed output ({msg[:200]}). Press Retry."
    if "503" in low or "unavailable" in low or "overloaded" in low:
        return "The Gemini model is overloaded right now (503). Wait a minute and press Retry, or pick another model in Settings."
    if "429" in low or "resource_exhausted" in low or "quota" in low:
        return "Gemini rate limit / quota exceeded. Wait a minute and press Retry."
    return f"Gemini call failed: {msg[:400]}"


def with_retries(fn: Callable[[], T], max_retries: int = 3, base_delay: float = 2.0) -> T:
    last: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            return fn()
        except LLMError:
            raise
        except Exception as exc:  # noqa: BLE001 - SDK raises many types
            last = exc
            if is_daily_quota(exc):
                raise DailyQuotaError("Daily free-tier quota for this Gemini model is used up.") from exc
            if attempt >= max_retries or not _is_retryable(exc):
                break
            delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
            log.warning("Gemini call failed (%s), retrying in %.1fs", exc, delay)
            time.sleep(delay)
    assert last is not None
    raise LLMError(_friendly(last)) from last


# --------------------------------------------------------------------------- #
# Gemini implementation
# --------------------------------------------------------------------------- #
class GeminiClient:
    # Models whose daily free-tier quota ran out in this process (shared by all instances).
    _exhausted: set[str] = set()

    def __init__(self, settings: Settings):
        if not settings.gemini_api_key:
            raise LLMError("GEMINI_API_KEY is not set. Copy .env.example to .env and add your key "
                           "(free key: https://aistudio.google.com/apikey).")
        from google import genai  # imported lazily so tests don't need the SDK
        from google.genai import types

        self._types = types
        self.settings = settings
        self.client = genai.Client(api_key=settings.gemini_api_key)

    def _run(self, make_call: Callable[[str], T], model: str | None, retries: int,
             allow_fallback: bool = True) -> T:
        """Call with the requested model; if its *daily* quota is used up, move on to the
        configured fallback models (free-tier quotas are per model)."""
        primary = model or self.settings.model
        chain = [primary] + ([m for m in self.settings.fallback_models if m != primary] if allow_fallback else [])
        tried = []
        for name in chain:
            if name in self._exhausted:
                continue
            tried.append(name)
            try:
                return with_retries(lambda: make_call(name), retries)
            except DailyQuotaError:
                log.warning("Daily quota exhausted for %s; trying the next model", name)
                self._exhausted.add(name)
        raise LLMError("The daily free-tier Gemini quota is used up for "
                       + (", ".join(tried) or ", ".join(chain))
                       + ". Quotas reset daily (midnight Pacific time). Add another model to "
                         "GEMINI_FALLBACK_MODELS, enable billing, or press Retry tomorrow.")

    # -- grounded (Google Search tool) -------------------------------------- #
    def grounded(self, prompt: str, system: str, model: str | None = None,
                 temperature: float = 0.2, retries: int | None = None) -> GroundedResult:
        types = self._types
        cfg = types.GenerateContentConfig(
            system_instruction=system,
            temperature=temperature,
            tools=[types.Tool(google_search=types.GoogleSearch())],
        )

        def call(name: str) -> GroundedResult:
            resp = self.client.models.generate_content(model=name, contents=prompt, config=cfg)
            return _grounding(resp, _response_text(resp))

        try:
            return self._run(call, model, self.settings.max_retries if retries is None else retries,
                             allow_fallback=False)
        except LLMError as exc:
            # Make the "grounding has no quota" case recognisable for the research fallback.
            raise LLMError(f"Google Search grounding quota unavailable: {exc}") from exc

    # -- plain text --------------------------------------------------------- #
    def generate(self, prompt: str, system: str, model: str | None = None,
                 temperature: float = 0.3) -> str:
        cfg = self._types.GenerateContentConfig(system_instruction=system, temperature=temperature)

        def call(name: str) -> str:
            resp = self.client.models.generate_content(model=name, contents=prompt, config=cfg)
            return _response_text(resp)

        return self._run(call, model, self.settings.max_retries)

    # -- structured JSON ---------------------------------------------------- #
    def structured(self, prompt: str, schema: type[T], system: str, model: str | None = None,
                   temperature: float = 0.3) -> T:
        types = self._types
        cfg = types.GenerateContentConfig(
            system_instruction=system,
            temperature=temperature,
            response_mime_type="application/json",
            response_schema=schema,
        )

        def call(name: str) -> T:
            resp = self.client.models.generate_content(model=name, contents=prompt, config=cfg)
            parsed = getattr(resp, "parsed", None)
            if isinstance(parsed, schema):
                return parsed
            text = _response_text(resp)
            try:
                return parse_model(text, schema)
            except (ValueError, ValidationError) as exc:
                raise InvalidJSONError(f"model returned invalid JSON ({exc})") from exc

        return self._run(call, model, self.settings.max_retries)


def _response_text(resp) -> str:
    text = getattr(resp, "text", None)
    if text:
        return text
    reason = ""
    try:
        reason = str(resp.candidates[0].finish_reason)
    except Exception:  # noqa: BLE001
        pass
    feedback = getattr(resp, "prompt_feedback", None)
    raise LLMError(f"Gemini returned an empty response (finish reason: {reason or 'unknown'}"
                   f"{', feedback: ' + str(feedback) if feedback else ''}). Press Retry.")


def _grounding(resp, text: str) -> GroundedResult:
    result = GroundedResult(text=text)
    try:
        gm = resp.candidates[0].grounding_metadata
    except Exception:  # noqa: BLE001
        gm = None
    if not gm:
        return result
    for chunk in gm.grounding_chunks or []:
        web = getattr(chunk, "web", None)
        if web and web.uri:
            result.sources.append({"title": web.title or "", "uri": web.uri})
    result.queries = list(gm.web_search_queries or [])
    for sup in gm.grounding_supports or []:
        seg = getattr(sup, "segment", None)
        result.supports.append({
            "text": getattr(seg, "text", "") if seg else "",
            "source_indices": list(sup.grounding_chunk_indices or []),
        })
    return result
