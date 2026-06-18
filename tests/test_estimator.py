"""Unit tests for macro-JSON parsing and normalization (P7).

Covers the pure functions in :mod:`daytracker.estimator` that turn a model's raw
response into a :class:`MealEstimate`: ``loads_json_object`` (tolerating ```json
fences), the ``_to_int`` / ``_to_grams`` coercions, and ``parse_estimate`` (which
always recomputes meal totals from the per-item numbers and drops junk items).
No network, no SDK — these are the unit tests the plan calls for.
"""

from __future__ import annotations

import pytest

from daytracker.estimator import (
    _to_grams,
    _to_int,
    loads_json_object,
    parse_estimate,
)

# --- loads_json_object --------------------------------------------------------


def test_loads_plain_object() -> None:
    assert loads_json_object('{"a": 1}') == {"a": 1}


def test_loads_tolerates_surrounding_whitespace() -> None:
    assert loads_json_object('  \n {"a": 1}\n  ') == {"a": 1}


def test_loads_strips_json_fence() -> None:
    assert loads_json_object('```json\n{"a": 1}\n```') == {"a": 1}


def test_loads_strips_bare_fence() -> None:
    assert loads_json_object('```\n{"a": 1}\n```') == {"a": 1}


@pytest.mark.parametrize("raw", ["", "   ", "not json at all", "{broken", "null"])
def test_loads_returns_none_on_garbage(raw: str) -> None:
    assert loads_json_object(raw) is None


@pytest.mark.parametrize("raw", ["[1, 2, 3]", "42", '"a string"'])
def test_loads_returns_none_when_not_an_object(raw: str) -> None:
    # Valid JSON, but not a JSON object -> not usable as a payload.
    assert loads_json_object(raw) is None


# --- _to_int / _to_grams ------------------------------------------------------


@pytest.mark.parametrize(
    ("value", "expected"),
    [(1.4, 1), (1.6, 2), (10, 10), ("3", 3), ("3.7", 4), (-5, 0), (-0.4, 0), (None, 0), ("abc", 0)],
)
def test_to_int(value: object, expected: int) -> None:
    assert _to_int(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [(None, None), (0, None), (-1, None), (50, 50.0), (40.5, 40.5), ("50", 50.0), ("abc", None)],
)
def test_to_grams(value: object, expected: float | None) -> None:
    assert _to_grams(value) == expected


# --- parse_estimate -----------------------------------------------------------


def test_parse_recomputes_totals_from_items() -> None:
    payload = {
        "items": [
            {"name": "orez", "grams": 40, "kcal": 52, "protein": 1, "carbs": 11, "fat": 0},
            {
                "name": "piept de pui",
                "grams": 100,
                "kcal": 165,
                "protein": 31,
                "carbs": 0,
                "fat": 4,
            },
        ],
        # A bogus model-supplied total must be ignored — totals come from the items.
        "kcal": 9999,
        "approximate": False,
        "note": None,
    }
    estimate = parse_estimate(payload)
    assert estimate is not None
    assert (estimate.kcal, estimate.protein_g, estimate.carbs_g, estimate.fat_g) == (217, 32, 11, 4)
    assert len(estimate.items) == 2
    assert estimate.items[0].name == "orez"
    assert estimate.items[0].grams == 40.0
    assert estimate.approximate is False
    assert estimate.note is None


def test_parse_drops_items_without_a_name_and_non_dicts() -> None:
    payload = {
        "items": [
            {"name": "  ", "kcal": 100},  # blank name -> dropped
            "not a dict",  # wrong type -> skipped
            {"kcal": 50},  # missing name -> dropped
            {"name": "ou", "kcal": 78, "protein": 6, "carbs": 1, "fat": 5},
        ]
    }
    estimate = parse_estimate(payload)
    assert estimate is not None
    assert len(estimate.items) == 1
    assert estimate.items[0].name == "ou"
    assert estimate.kcal == 78


def test_parse_clamps_negative_numbers_to_zero() -> None:
    payload = {"items": [{"name": "x", "kcal": -100, "protein": -3, "carbs": -1, "fat": -2}]}
    estimate = parse_estimate(payload)
    assert estimate is not None
    assert (estimate.kcal, estimate.protein_g, estimate.carbs_g, estimate.fat_g) == (0, 0, 0, 0)


@pytest.mark.parametrize(
    "payload",
    [
        {"items": []},  # empty list
        {"items": "rice"},  # items not a list
        {"items": [{"name": ""}, "junk"]},  # no usable item survives
        {},  # missing "items"
    ],
)
def test_parse_returns_none_when_no_usable_item(payload: dict) -> None:
    assert parse_estimate(payload) is None


def test_parse_note_is_trimmed_or_none() -> None:
    assert parse_estimate(
        {"items": [{"name": "x", "kcal": 1}], "note": "  porție medie  "}
    ).note == ("porție medie")
    assert parse_estimate({"items": [{"name": "x", "kcal": 1}], "note": "   "}).note is None
    assert parse_estimate({"items": [{"name": "x", "kcal": 1}]}).note is None


def test_parse_approximate_flag_passthrough() -> None:
    assert parse_estimate({"items": [{"name": "x", "kcal": 1}], "approximate": True}).approximate
    assert not parse_estimate({"items": [{"name": "x", "kcal": 1}]}).approximate


def test_parse_grams_normalized() -> None:
    # zero/negative grams -> None; a numeric string -> float.
    payload = {
        "items": [
            {"name": "a", "grams": 0, "kcal": 1},
            {"name": "b", "grams": "120", "kcal": 1},
        ]
    }
    estimate = parse_estimate(payload)
    assert estimate is not None
    assert estimate.items[0].grams is None
    assert estimate.items[1].grams == 120.0
