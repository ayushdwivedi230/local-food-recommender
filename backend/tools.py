"""The actual restaurant tools used by the agent loop.

The exact tool names are intentionally simple for a course demonstration:
find_restaurants(city) and filter_by_cuisine(type).
"""

from __future__ import annotations

import json
import os
from typing import Any

DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "restaurants.json")
_last_search_results: list[dict[str, Any]] = []


def _load_restaurants() -> list[dict[str, Any]]:
    with open(DATA_PATH, "r", encoding="utf-8") as handle:
        return json.load(handle)


def find_restaurants(city: str) -> list[dict[str, Any]]:
    """Find restaurants in a city and store the observation for the next tool."""
    global _last_search_results
    normalized = city.strip().casefold()
    if normalized == "simulate tool error":
        raise RuntimeError("The local restaurant index is unavailable.")
    _last_search_results = [
        restaurant
        for restaurant in _load_restaurants()
        if restaurant["city"].casefold() == normalized
    ]
    return list(_last_search_results)


def filter_by_cuisine(type: str) -> list[dict[str, Any]]:
    """Filter the previous find_restaurants observation by cuisine."""
    normalized = type.strip().casefold()
    return [
        restaurant
        for restaurant in _last_search_results
        if any(cuisine.casefold() == normalized for cuisine in restaurant["cuisine"])
    ]