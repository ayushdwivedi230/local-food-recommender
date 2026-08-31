"""Explicit plan-act-observe-decide agent for LocalFood AI."""

from __future__ import annotations

import re
import time
from typing import Any

from memory import get_memory, save_memory
from tools import filter_by_cuisine, find_restaurants

CITIES = ["Jalandhar", "Phagwara", "Ludhiana", "Amritsar", "Chandigarh", "Delhi", "Bengaluru"]
CUISINES = ["Punjabi", "North Indian", "South Indian", "Chinese", "Italian", "Mughlai", "Street Food", "Fast Food", "Cafe", "Jain"]
LOCATION_ALIASES = {"koramangala": "Bengaluru", "indiranagar": "Bengaluru"}

# ---------------------------------------------------------------------------
# Intent classification — keeps greetings and help requests out of the
# restaurant-search loop without changing any existing food-request logic.
# ---------------------------------------------------------------------------

_GREETING_PATTERNS = re.compile(
    r"^\s*(hi+|hello+|hey+|howdy|good\s+(morning|afternoon|evening|day)|namaste|namaskar|sat\s+sri\s+akal)\b",
    re.IGNORECASE,
)
_CAPABILITY_PATTERNS = re.compile(
    r"\b(what\s+can\s+you\s+do|what\s+do\s+you\s+do|how\s+do\s+you\s+work|help|capabilities|features|tell\s+me\s+about\s+yourself|about\s+you)\b",
    re.IGNORECASE,
)
_HUNGRY_PATTERNS = re.compile(
    r"^\s*(i'?m?\s+hungry|feeling\s+hungry|starving|i\s+want\s+to\s+eat|i\s+need\s+food)\s*[!.?]*\s*$",
    re.IGNORECASE,
)
_FOOD_REQUEST_PATTERNS = re.compile(
    r"\b(restaurant|food|eat|hungry|cuisine|recommend|find|search|veg|non.?veg|diet|spicy|budget|"
    + "|".join(city.casefold() for city in CITIES)
    + "|"
    + "|".join(c.casefold() for c in CUISINES)
    + r")\b",
    re.IGNORECASE,
)


def _classify_intent(message: str) -> str:
    """Return one of: 'greeting', 'capability', 'hungry', 'food', 'preference'.

    'food' and 'preference' both feed into the agentic search loop.
    Everything else gets a short conversational reply with no tool calls.
    """
    text = message.strip()
    if _GREETING_PATTERNS.match(text):
        return "greeting"
    if _CAPABILITY_PATTERNS.search(text):
        return "capability"
    if _HUNGRY_PATTERNS.match(text):
        return "hungry"
    return "food"  # default — run the full agentic loop


def _conversational_response(session_id: str, intent: str, message: str, started: float) -> dict[str, Any]:
    """Build a lightweight non-agentic response for greetings and help."""
    memory = get_memory(session_id)
    if intent == "greeting":
        reply = (
            "Hi there! 👋 I'm LocalFood AI — your local food recommender. "
            "Tell me your city, preferred cuisine, or dietary needs and I'll find the best options for you. "
            "Try: \"I'm vegetarian and I want Punjabi food in Jalandhar.\""
        )
        label = "Greeting"
        detail = "Recognised a greeting — no restaurant search needed."
    elif intent == "capability":
        reply = (
            "Here's what I can do:\n\n"
            "🔍 **find_restaurants(city)** — searches the local restaurant index for a city\n"
            "🍽️ **filter_by_cuisine(type)** — narrows those results to a specific cuisine\n"
            "🧠 **Memory** — I remember your diet, cuisine preference, spice level, and budget across turns\n"
            "🛡️ **Dietary guardrail** — I never recommend a restaurant that violates your dietary requirement\n"
            "📊 **Ranking** — I score each safe result on cuisine match, diet, rating, budget, and distance\n\n"
            "Try: \"I'm vegetarian and I like Punjabi food in Jalandhar.\""
        )
        label = "Capability query"
        detail = "User asked what the agent can do — returned capability summary without calling any tools."
    else:  # hungry
        reply = (
            "I can help with that! Which city are you in? "
            "You can also tell me your cuisine preference, diet (vegetarian / vegan / Jain), "
            "spice level, or budget and I'll search the local index for you."
        )
        label = "Hunger signal"
        detail = "User is hungry but provided no location or preference — asking for details."

    activity = [
        _event("understand", "thought", "Understanding your request", detail),
        _event("intent", "decision", label, "No restaurant tools needed for this message type."),
    ]
    trace = [
        _trace(1, "Intent", "intent", f'User said: "{message.strip()}" — classified as {intent}.'),
        _trace(2, "Decision", "decision", f"Agent chose conversational reply; skipped find_restaurants and filter_by_cuisine."),
    ]
    return _response(session_id, reply, memory, activity, trace, [], 0, 0, 0, started)


# ---------------------------------------------------------------------------
# Preference extraction helpers
# ---------------------------------------------------------------------------

def _event(event_id: str, kind: str, label: str, detail: str, status: str = "complete") -> dict[str, str]:
    return {"id": event_id, "kind": kind, "label": label, "detail": detail, "status": status}


def _trace(step: int, title: str, type_: str, detail: str, tool: str | None = None, arguments: dict[str, Any] | None = None, result: str | None = None) -> dict[str, Any]:
    return {
        "step": step,
        "title": title,
        "type": type_,
        "detail": detail,
        "tool": tool,
        "arguments": arguments,
        "result": result,
    }


def _extract_preferences(message: str, existing: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    text = message.casefold()
    updated = dict(existing)
    detected: dict[str, Any] = {}
    if re.search(r"\b(not\s+vegetarian|non[- ]?vegetarian|nonveg|non-veg)\b", text):
        detected["diet"] = "non-vegetarian"
    elif re.search(r"\b(vegetarian|veg)\b", text):
        detected["diet"] = "vegetarian"
    elif "vegan" in text:
        detected["diet"] = "vegan-friendly"
    elif "jain" in text:
        detected["diet"] = "Jain-friendly"

    for cuisine in CUISINES:
        if cuisine.casefold() in text:
            detected["preferredCuisine"] = cuisine
            break
    # Explicit negative taste statements must be handled before positive
    # keyword matching.  Otherwise "I don't like spicy food" contains the word
    # "spicy" and would incorrectly become a positive spicy preference.
    disliked = re.search(
        r"(?:don't\s+like|do\s+not\s+like|dont\s+like|dislike|avoid|hate)\s+([a-z][a-z -]{2,24})",
        text,
    )
    if disliked:
        disliked_value = disliked.group(1).strip().title()
        # Only store a disliked cuisine when the captured phrase is actually
        # one of the supported cuisines.  "spicy food" is not a cuisine.
        known_cuisines = {c.casefold() for c in CUISINES}
        if disliked_value.casefold() in known_cuisines:
            detected["dislikedCuisine"] = disliked_value

    negative_spice = re.search(
        r"\b(?:don't|do not|dont|dislike|avoid|hate)\s+(?:like\s+)?"
        r"(?:very\s+|too\s+)?spicy\b",
        text,
    )
    if negative_spice:
        detected["spicePreference"] = "mild"
    elif re.search(
        r"\b(mild|not\s+(?:too\s+)?spicy|less\s+spicy)\b",
        text,
    ):
        detected["spicePreference"] = "mild"
    elif re.search(r"\b(spicy|spice|hot|fiery)\b", text):
        detected["spicePreference"] = "spicy"
    budget = re.search(r"(?:under|below|within|budget(?:\s+of)?)[^\d₹]{0,8}₹?\s*(\d{2,5})", text)
    if budget:
        detected["budget"] = float(budget.group(1))
    for city in CITIES:
        if city.casefold() in text:
            detected["location"] = city
            break
    if "location" not in detected:
        neighborhood = re.search(r"\b(?:in|near|around)\s+([a-z][a-z -]{2,24})", text)
        if neighborhood:
            place = neighborhood.group(1).strip().split(" under ")[0].split(" tonight")[0].strip()
            detected["location"] = LOCATION_ALIASES.get(place.casefold(), place.title())
    updated.update(detected)
    return updated, detected


def _memory_summary(memory: dict[str, Any]) -> str:
    """Return only meaningful active preferences for the activity panel."""
    labels = {
        "diet": "diet",
        "preferredCuisine": "cuisine",
        "spicePreference": "spicePreference",
        "budget": "budget",
        "location": "location",
    }
    parts = []
    for key, label in labels.items():
        value = memory.get(key)
        if value not in (None, "", []):
            parts.append(f"{label}: {value}")
    return " + ".join(parts) if parts else "No preferences stored yet."


def _diet_compatible(restaurant: dict[str, Any], diet: str | None) -> bool:
    if not diet:
        return True
    labels = {label.casefold() for label in restaurant["diet"]}
    if diet == "vegetarian":
        return "vegetarian" in labels or "vegan-friendly" in labels
    if diet == "vegan-friendly":
        return "vegan-friendly" in labels
    if diet == "jain-friendly":
        return "jain-friendly" in labels
    if diet == "non-vegetarian":
        return "non-vegetarian" in labels
    return True


def _rank(restaurants: list[dict[str, Any]], preferences: dict[str, Any]) -> list[dict[str, Any]]:
    cuisine = preferences.get("preferredCuisine")
    budget = preferences.get("budget")
    spice = preferences.get("spicePreference")
    ranked: list[dict[str, Any]] = []
    for restaurant in restaurants:
        cuisine_match = 1.0 if cuisine and cuisine.casefold() in {item.casefold() for item in restaurant["cuisine"]} else 0.55
        budget_match = 1.0 if budget and restaurant["average_price"] <= budget else (0.65 if budget else 0.7)
        if spice:
            desired_spice = "high" if spice == "spicy" else "low"
            taste_match = 1.0 if restaurant["spice_level"] == desired_spice else 0.35
        else:
            taste_match = 0.7
        rating_score = restaurant["rating"] / 5
        distance_score = max(0.0, 1 - (restaurant["distance_km"] / 10))
        breakdown = {
            "cuisine": round(cuisine_match * 0.30, 3),
            "diet": 0.30,
            "rating": round(rating_score * 0.15, 3),
            "budget": round(budget_match * 0.10, 3),
            "taste": round(taste_match * 0.10, 3),
            "distance": round(distance_score * 0.05, 3),
        }
        score = round(sum(breakdown.values()) * 100, 1)
        reason_parts = []
        if cuisine:
            reason_parts.append(f"matches your {cuisine} preference")
        if preferences.get("diet"):
            reason_parts.append(f"is compatible with a {preferences['diet']} diet")
        reason_parts.append(f"has a {restaurant['rating']:.1f} rating")
        if budget and restaurant["average_price"] <= budget:
            reason_parts.append(f"fits your ₹{int(budget)} budget")
        if spice and ((spice == "spicy" and restaurant["spice_level"] == "high") or (spice == "mild" and restaurant["spice_level"] == "low")):
            reason_parts.append(f"leans {restaurant['spice_level']}-spice")
        reason_parts.append(f"it's only {restaurant['distance_km']:.1f} km away")
        ranked.append({
            **restaurant,
            "score": score,
            "reason": "Recommended because it " + ", ".join(reason_parts[:-1]) + f", and {reason_parts[-1]}.",
            "scoreBreakdown": breakdown,
        })
    return sorted(ranked, key=lambda item: (-item["score"], -item["rating"], item["distance_km"]))


# ---------------------------------------------------------------------------
# Main agent entry point
# ---------------------------------------------------------------------------

def run_agent(session_id: str, message: str) -> dict[str, Any]:
    started = time.perf_counter()

    # ── Intent gate ─────────────────────────────────────────────────────────
    # Classify before doing anything else. Greetings, help requests, and
    # "I'm hungry" prompts get a friendly reply without calling any tools.
    # Food/preference requests fall through to the full agentic loop below.
    intent = _classify_intent(message.strip())
    if intent in ("greeting", "capability", "hungry"):
        return _conversational_response(session_id, intent, message, started)
    # ── End intent gate ──────────────────────────────────────────────────────

    memory_before = get_memory(session_id)
    memory, detected = _extract_preferences(message.strip(), memory_before)
    activity = [
        _event("understand", "thought", "Understanding your request", "Parsing the latest message and retrieving remembered preferences."),
        _event("memory", "observation", "Memory read", _memory_summary(memory_before)),
    ]
    trace = [
        _trace(1, "Intent", "intent", f"User asked: \"{message.strip()}\""),
        _trace(2, "Memory", "memory", f"Read memory: {memory_before}"),
    ]

    # Dietary requirements are hard constraints.  A new non-vegetarian
    # request must not silently overwrite an already remembered vegetarian
    # requirement in the same session.
    conflict = (
        memory_before.get("diet") == "vegetarian"
        and detected.get("diet") == "non-vegetarian"
    )
    if conflict:
        memory = memory_before
    elif detected:
        memory = save_memory(session_id, memory)
        changed = ", ".join(f"{key.replace('preferredCuisine', 'cuisine')} = {value}" for key, value in detected.items())
        activity.append(_event("memory-write", "decision", "Memory updated", f"Remembering {changed}."))
        trace.append(_trace(3, "Memory write", "memory", f"Updated preferences from this turn: {detected}"))
    else:
        memory = save_memory(session_id, memory)

    # Re-read the full merged memory so cross-turn preferences (cuisine, diet
    # set in a previous turn) are always available for this turn's search.
    requested_city = memory.get("location")
    requested_cuisine = memory.get("preferredCuisine")

    if conflict:
        reply = "I noticed a conflict: your remembered preference is vegetarian, but this turn asks for non-vegetarian food. I have not recommended anything yet—tell me if you'd like me to update that dietary preference."
        activity.append(_event("conflict", "warning", "Dietary conflict detected", "Hard dietary constraints prevent an unsafe recommendation."))
        trace.append(_trace(4, "Safety check", "decision", "Stopped before searching because the new request conflicts with remembered vegetarian requirements."))
        return _response(session_id, reply, memory, activity, trace, [], 0, 0, 0, started)

    if not requested_city:
        if detected:
            reply = "Got it — I'll remember those preferences. Which city should I search in?"
        else:
            reply = "Sure. Which city should I search in? You can also mention a cuisine, diet, spice level, or budget."
        activity.append(_event("clarify", "decision", "Need one detail", "A city is required before the restaurant search can begin."))
        trace.append(_trace(4, "Next action", "decision", "Ask for a city instead of calling a search tool with an incomplete location."))
        return _response(session_id, reply, memory, activity, trace, [], 0, 0, 0, started)

    activity.append(_event("plan", "decision", "Plan formed", "Search the city, narrow cuisine if needed, enforce diet, then rank safe options."))
    trace.append(_trace(4, "Plan", "plan", "The next action is selected from the current state: search first, then inspect the observation before choosing another tool."))
    try:
        activity.append(_event("find-call", "tool", "Calling find_restaurants()", f"Searching the local index for {requested_city}."))
        trace.append(_trace(5, "Tool Call", "tool", "The agent chose the search tool because a city is available.", "find_restaurants", {"city": requested_city}))
        search_results = find_restaurants(requested_city)
        trace[-1]["result"] = f"{len(search_results)} restaurants found"
        activity.append(_event("find-result", "observation", "Restaurant search complete", f"Found {len(search_results)} restaurants in {requested_city}."))
        trace.append(_trace(6, "Tool Result", "observation", f"find_restaurants returned {len(search_results)} structured records.", result=f"{len(search_results)} restaurants found"))
    except Exception:
        activity.append(_event("tool-error", "warning", "Search temporarily failed", "The tool reported an error; no result was fabricated."))
        trace.append(_trace(6, "Tool Result", "observation", "The restaurant tool raised an error.", "find_restaurants", {"city": requested_city}, "Tool error"))
        return _response(session_id, "Restaurant search temporarily failed. Please try again.", memory, activity, trace, [], 0, 0, 0, started)

    if not search_results:
        activity.append(_event("no-city", "warning", "No restaurants found", f"The dataset has no entries for {requested_city}."))
        trace.append(_trace(7, "Agent Decision", "decision", "No search results were returned, so the loop ends honestly without a second tool call."))
        return _response(session_id, f"I couldn't find restaurants in {requested_city}. Try Jalandhar, Phagwara, Ludhiana, Amritsar, Chandigarh, Delhi, or Bengaluru.", memory, activity, trace, [], 0, 0, 0, started)

    cuisine_results = search_results
    if requested_cuisine:
        activity.append(_event("cuisine-call", "tool", "Calling filter_by_cuisine()", f"Narrowing the observation to {requested_cuisine}."))
        trace.append(_trace(7, "Tool Call", "tool", "The search returned results, so the agent chose a cuisine filter next.", "filter_by_cuisine", {"type": requested_cuisine}))
        cuisine_results = filter_by_cuisine(requested_cuisine)
        trace[-1]["result"] = f"{len(cuisine_results)} cuisine matches"
        activity.append(_event("cuisine-result", "observation", "Cuisine filter complete", f"Found {len(cuisine_results)} {requested_cuisine} matches."))
        trace.append(_trace(8, "Tool Result", "observation", f"filter_by_cuisine returned {len(cuisine_results)} records.", result=f"{len(cuisine_results)} cuisine matches"))

    diet_results = [restaurant for restaurant in cuisine_results if _diet_compatible(restaurant, memory.get("diet"))]
    removed = len(cuisine_results) - len(diet_results)
    activity.append(_event("diet-filter", "decision", "Applying dietary guardrail", f"Kept {len(diet_results)} options; removed {removed} incompatible option(s)."))
    trace.append(_trace(9, "Filtering", "filter", f"Applied hard dietary requirement: {memory.get('diet') or 'none'}. {len(diet_results)} remain."))

    if not diet_results:
        if requested_cuisine:
            reply = f"I found restaurants in {requested_city}, but none matched {requested_cuisine} while satisfying your {memory.get('diet')} requirement."
        else:
            reply = f"I found restaurants in {requested_city}, but none satisfy your {memory.get('diet')} requirement."
        activity.append(_event("no-diet-match", "warning", "No safe match", "Dietary requirements are hard constraints, so incompatible options are not recommended."))
        trace.append(_trace(10, "Final Recommendation", "result", "No safe recommendation exists for every active constraint."))
        return _response(session_id, reply, memory, activity, trace, [], len(search_results), len(cuisine_results), 0, started)

    ranked = _rank(diet_results, memory)
    activity.append(
        _event(
            "rank",
            "decision",
            "Ranking remaining options",
            "Scoring cuisine, diet, rating, budget, taste, and distance using the current remembered preferences.",
        )
    )
    activity.append(_event("ready", "success", "Recommendation ready", f"Ranked {len(ranked)} safe match(es)."))
    trace.append(_trace(10, "Final Recommendation", "result", "Returned ranked candidates with transparent score breakdowns."))
    best = ranked[0]
    reply = f"I found {len(ranked)} safe match{'es' if len(ranked) != 1 else ''} in {requested_city}. {best['name']} is the strongest overall fit at {best['score']}/100."
    return _response(session_id, reply, memory, activity, trace, ranked[:5], len(search_results), len(cuisine_results), len(diet_results), started)


def _response(session_id: str, reply: str, memory: dict[str, Any], activity: list[dict[str, Any]], trace: list[dict[str, Any]], recommendations: list[dict[str, Any]], searched: int, after_cuisine: int, after_diet: int, started: float) -> dict[str, Any]:
    public_recommendations = []
    for restaurant in recommendations:
        public_recommendations.append({
            "id": restaurant["id"],
            "name": restaurant["name"],
            "city": restaurant["city"],
            "cuisine": restaurant["cuisine"],
            "diet": restaurant["diet"],
            "rating": restaurant["rating"],
            "averagePrice": restaurant["average_price"],
            "priceRange": restaurant["price_range"],
            "spiceLevel": restaurant["spice_level"],
            "distanceKm": restaurant["distance_km"],
            "description": restaurant["description"],
            "score": restaurant["score"],
            "reason": restaurant["reason"],
            "scoreBreakdown": restaurant["scoreBreakdown"],
        })
    return {
        "sessionId": session_id,
        "mode": "demo",
        "reply": reply,
        "memory": memory,
        "activity": activity,
        "trace": trace,
        "recommendations": public_recommendations,
        "stats": {
            "searched": searched,
            "afterCuisine": after_cuisine,
            "afterDiet": after_diet,
            "elapsedMs": max(1, round((time.perf_counter() - started) * 1000)),
        },
    }
