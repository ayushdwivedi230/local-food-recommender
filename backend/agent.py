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
    disliked = re.search(r"(?:don't like|dislike|avoid|hate)\s+([a-z][a-z -]{2,24})", text)
    if disliked:
        detected["dislikedCuisine"] = disliked.group(1).strip().title()
    if re.search(r"\b(mild|not\s+(?:too\s+)?spicy|less\s+spicy)\b", text):
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
        taste_match = 1.0 if spice and restaurant["spice_level"] == ("high" if spice == "spicy" else "low") else (0.7 if spice else 0.7)
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


def run_agent(session_id: str, message: str) -> dict[str, Any]:
    started = time.perf_counter()
    memory_before = get_memory(session_id)
    memory, detected = _extract_preferences(message.strip(), memory_before)
    activity = [
        _event("understand", "thought", "Understanding your request", "Parsing the latest message and retrieving remembered preferences."),
        _event("memory", "observation", "Memory read", " + ".join(f"{key}: {value}" for key, value in memory_before.items() if value and key != "updatedAt") or "No preferences stored yet."),
    ]
    trace = [
        _trace(1, "Intent", "intent", f"User asked: “{message.strip()}”"),
        _trace(2, "Memory", "memory", f"Read memory: {memory_before}"),
    ]

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

    requested_city = memory.get("location")
    requested_cuisine = memory.get("preferredCuisine")
    if conflict:
        reply = "I noticed a conflict: your remembered preference is vegetarian, but this turn asks for non-vegetarian food. I have not recommended anything yet—tell me if you'd like me to update that dietary preference."
        activity.append(_event("conflict", "warning", "Dietary conflict detected", "Hard dietary constraints prevent an unsafe recommendation."))
        trace.append(_trace(4, "Safety check", "decision", "Stopped before searching because the new request conflicts with remembered vegetarian requirements."))
        return _response(session_id, reply, memory, activity, trace, [], 0, 0, 0, started)

    if not requested_city:
        if detected:
            reply = "Got it — I’ll remember those preferences. Which city should I search in?"
        else:
            reply = "Sure. Which city should I search in? You can also mention a cuisine, diet, spice level, or budget."
        activity.append(_event("clarify", "decision", "Need one detail", "A city is required before the restaurant search can begin."))
        trace.append(_trace(4, "Next action", "decision", "Ask for a city instead of calling a search tool with an incomplete location."))
        return _response(session_id, reply, memory, activity, trace, [], 0, 0, 0, started)

    activity.append(_event("plan", "decision", "Plan formed", "Search the city, narrow cuisine if needed, enforce diet, then rank safe options."))
    trace.append(_trace(4, "Plan", "plan", "The next action is selected from the current state: search first, then inspect the observation before choosing another tool."))
    try:
        activity.append(_event("find-call", "tool", "Calling find_restaurants()", f'Searching the fictional local index for {requested_city}.'))
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
        activity.append(_event("no-city", "warning", "No restaurants found", f"The fictional dataset has no entries for {requested_city}."))
        trace.append(_trace(7, "Agent Decision", "decision", "No search results were returned, so the loop ends honestly without a second tool call."))
        return _response(session_id, f"I couldn’t find restaurants in {requested_city}. Try Jalandhar, Phagwara, Ludhiana, Amritsar, Chandigarh, Delhi, or Bengaluru.", memory, activity, trace, [], 0, 0, 0, started)

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
    activity.append(_event("rank", "decision", "Ranking remaining options", "Scoring cuisine, diet, rating, budget, taste, and distance."))
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