"""Macro estimation: turn a Romanian meal description into per-item macros.

All LLM access goes through the :class:`MacroEstimator` protocol so the provider
can be swapped without touching call sites (DECISIONS.md, 2026-06-17). The default
provider is Google Gemini Flash on the free tier; ``MACRO_PROVIDER=fake`` selects a
deterministic offline stand-in for local dev and tests.

The Gemini implementation takes an *ordered list* of models and falls through to the
next one when a model returns HTTP 429 (free-tier quota exhausted) — each model has
its own quota bucket, so the chain buys more daily headroom (DECISIONS.md, 2026-06-18).
Within a model, a *transient* failure (request timeout, 5xx, connection error) is
retried up to :data:`RETRY_ATTEMPTS` times with a short exponential backoff before the
chain moves on (P7 hardening — DECISIONS.md, 2026-06-18).

JSON normalization (:func:`parse_estimate`) is a pure function: meal totals are always
recomputed from the per-item numbers rather than trusting the model's own totals.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from .config import ConfigError

if TYPE_CHECKING:
    from .config import Settings

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT_SECONDS = 30.0
# P7: retry a *transient* failure (timeout/5xx/connection) on the same model up to this
# many attempts before moving to the next model; 429 (quota) never retries — it falls
# straight through (DECISIONS.md, 2026-06-18).
RETRY_ATTEMPTS = 2
RETRY_BACKOFF_SECONDS = 1.0  # base delay before a retry; doubles each attempt

SYSTEM_INSTRUCTION = (
    "You are a nutrition estimator for a Romanian food-logging bot. The user sends a "
    "short Romanian description of a meal — foods and usually quantities in grams. "
    "Estimate the macronutrients for EACH distinct food item.\n\n"
    "Respond with ONLY a JSON object, no prose, of the form:\n"
    '{"items": [{"name": str, "grams": number|null, "kcal": number, '
    '"protein": number, "carbs": number, "fat": number}], '
    '"approximate": bool, "note": str|null}\n\n'
    "Rules:\n"
    "- Use the quantities given. If a quantity is missing or vague, assume a typical "
    'Romanian portion, fill "grams" with the amount you assumed, and set '
    '"approximate": true.\n'
    '- "name": a short Romanian name for the food.\n'
    '- "kcal", "protein", "carbs", "fat": estimated for that item\'s portion '
    "(kcal and grams), non-negative numbers.\n"
    '- "approximate": true if you guessed any portion or the input was vague; false if '
    "every quantity was explicit.\n"
    '- "note": optional very short Romanian note about an assumption, else null.\n'
    '- If the text contains no recognizable food, return an empty "items" array.'
)


@dataclass(frozen=True, slots=True)
class MacroItem:
    """One food item's estimated macros."""

    name: str
    grams: float | None
    kcal: int
    protein_g: int
    carbs_g: int
    fat_g: int


@dataclass(frozen=True, slots=True)
class MealEstimate:
    """A whole meal: its items plus totals recomputed from them."""

    items: list[MacroItem]
    kcal: int
    protein_g: int
    carbs_g: int
    fat_g: int
    approximate: bool
    note: str | None


class MacroEstimatorError(RuntimeError):
    """Raised when no estimate could be produced (all models failed/timed out)."""


class MacroEstimator(Protocol):
    """Provider-agnostic interface for estimating a meal's macros."""

    async def estimate(self, text: str) -> MealEstimate | None:
        """Estimate macros for ``text``.

        Returns ``None`` when the text contains no recognizable food. Raises
        :class:`MacroEstimatorError` when the backend is unavailable.
        """
        ...


# --- Pure parsing/normalization (no I/O — easy to unit-test in P7) -------------


def _to_int(value: object) -> int:
    """Coerce a model-supplied number to a non-negative int; 0 on garbage."""
    try:
        return max(0, round(float(value)))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0


def _to_grams(value: object) -> float | None:
    if value is None:
        return None
    try:
        grams = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return grams if grams > 0 else None


def parse_estimate(payload: dict) -> MealEstimate | None:
    """Normalize the model's JSON object into a :class:`MealEstimate`.

    Totals are summed from the items (the model's own totals, if any, are ignored).
    Returns ``None`` when no usable item is present.
    """
    raw_items = payload.get("items")
    if not isinstance(raw_items, list):
        return None

    items: list[MacroItem] = []
    for raw in raw_items:
        if not isinstance(raw, dict):
            continue
        name = str(raw.get("name") or "").strip()
        if not name:
            continue
        items.append(
            MacroItem(
                name=name,
                grams=_to_grams(raw.get("grams")),
                kcal=_to_int(raw.get("kcal")),
                protein_g=_to_int(raw.get("protein")),
                carbs_g=_to_int(raw.get("carbs")),
                fat_g=_to_int(raw.get("fat")),
            )
        )

    if not items:
        return None

    note_raw = payload.get("note")
    note = (str(note_raw).strip() or None) if note_raw is not None else None

    return MealEstimate(
        items=items,
        kcal=sum(i.kcal for i in items),
        protein_g=sum(i.protein_g for i in items),
        carbs_g=sum(i.carbs_g for i in items),
        fat_g=sum(i.fat_g for i in items),
        approximate=bool(payload.get("approximate", False)),
        note=note,
    )


_FENCE_RE = re.compile(r"^```(?:json)?|```$", re.IGNORECASE)


def loads_json_object(raw: str) -> dict | None:
    """Parse a JSON object from a model response, tolerating ```json fences."""
    text = (raw or "").strip()
    if not text:
        return None
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        cleaned = _FENCE_RE.sub("", text).strip()
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            return None
    return data if isinstance(data, dict) else None


# --- Gemini provider -----------------------------------------------------------


class GeminiMacroEstimator:
    """Gemini Flash estimator with an ordered model-fallback chain.

    ``google-genai`` is imported lazily so the package is only needed when this
    provider is actually used (the fake provider and unit tests don't pull it in).
    """

    def __init__(
        self,
        api_key: str,
        models: tuple[str, ...],
        *,
        timeout: float = REQUEST_TIMEOUT_SECONDS,
    ) -> None:
        from google import genai

        self._client = genai.Client(api_key=api_key)
        self._models = models
        self._timeout = timeout

    async def estimate(self, text: str) -> MealEstimate | None:
        from google.genai import errors, types

        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            response_mime_type="application/json",
            temperature=0.2,
        )

        last_error: Exception | None = None
        for model in self._models:
            for attempt in range(RETRY_ATTEMPTS):
                try:
                    response = await asyncio.wait_for(
                        self._client.aio.models.generate_content(
                            model=model, contents=text, config=config
                        ),
                        timeout=self._timeout,
                    )
                except errors.ClientError as exc:
                    # 429 = this model's free-tier quota is spent; a retry won't restore
                    # it, so move straight to the next model.
                    if exc.code == 429:
                        logger.warning("Gemini model %s rate-limited (429); trying next", model)
                        last_error = exc
                        break
                    # Other 4xx (bad key, bad request) won't be fixed by a retry or
                    # another model — fail fast.
                    logger.error("Gemini client error on %s: %s", model, exc)
                    raise MacroEstimatorError(str(exc)) from exc
                except (errors.ServerError, TimeoutError, ConnectionError) as exc:
                    # Transient: retry the same model with backoff, then fall through.
                    last_error = exc
                    if attempt + 1 < RETRY_ATTEMPTS:
                        delay = RETRY_BACKOFF_SECONDS * (2**attempt)
                        logger.warning(
                            "Gemini transient failure on %s (%s); retrying in %.0fs",
                            model,
                            exc,
                            delay,
                        )
                        await asyncio.sleep(delay)
                        continue
                    logger.warning("Gemini transient failure on %s (%s); trying next", model, exc)
                    break

                payload = loads_json_object(response.text or "")
                if payload is None:
                    # A retry at temperature 0.2 would likely repeat it — move on.
                    logger.warning("Gemini returned non-JSON on %s; trying next", model)
                    last_error = MacroEstimatorError("non-JSON response")
                    break
                return parse_estimate(payload)

        raise MacroEstimatorError("all configured Gemini models failed") from last_error


# --- Fake provider (offline, deterministic) ------------------------------------

_LEADING_GRAMS_RE = re.compile(r"^\s*(\d+(?:[.,]\d+)?)\s*(?:g|gr|grame)?\s+(.*)$", re.IGNORECASE)


def _split_items(text: str) -> list[str]:
    parts = re.split(r"[,;\n]+|\bși\b|\bsi\b|\+", text)
    return [p.strip() for p in parts if p.strip()]


class FakeMacroEstimator:
    """Deterministic, offline estimator for local dev and tests (no network).

    Not nutritionally accurate — it just exercises the parse/store/reply path with
    plausible, repeatable numbers using crude per-gram densities.
    """

    async def estimate(self, text: str) -> MealEstimate | None:
        items: list[MacroItem] = []
        for part in _split_items(text):
            match = _LEADING_GRAMS_RE.match(part)
            if match:
                grams: float | None = float(match.group(1).replace(",", "."))
                name = match.group(2).strip()
            else:
                grams, name = None, part
            if not name:
                continue
            basis = grams if grams is not None else 100.0
            items.append(
                MacroItem(
                    name=name,
                    grams=grams,
                    kcal=round(basis * 1.5),
                    protein_g=round(basis * 0.10),
                    carbs_g=round(basis * 0.15),
                    fat_g=round(basis * 0.05),
                )
            )
        if not items:
            return None
        return MealEstimate(
            items=items,
            kcal=sum(i.kcal for i in items),
            protein_g=sum(i.protein_g for i in items),
            carbs_g=sum(i.carbs_g for i in items),
            fat_g=sum(i.fat_g for i in items),
            approximate=True,
            note="estimare locală (fără AI)",
        )


# --- Factory -------------------------------------------------------------------


def create_estimator(settings: Settings) -> MacroEstimator:
    """Build the estimator selected by ``MACRO_PROVIDER`` (fail-fast on misconfig)."""
    if settings.macro_provider == "fake":
        return FakeMacroEstimator()
    if settings.macro_provider == "gemini":
        if not settings.gemini_api_key:
            raise ConfigError("GEMINI_API_KEY is required when MACRO_PROVIDER=gemini.")
        return GeminiMacroEstimator(settings.gemini_api_key, settings.gemini_models)
    # config.load_settings already validates the provider, so this is defensive.
    raise ConfigError(f"Unknown MACRO_PROVIDER: {settings.macro_provider!r}")
