
from __future__ import annotations

import re
import time
from typing import Any

from memory import get_memory, save_memory
from tools import filter_by_cuisine, find_restaurants

CITIES = [
    "Jalandhar", "Phagwara", "Ludhiana", "Amritsar",
    "Chandigarh", "Delhi", "Bengaluru",
]

CUISINES = [
    "Punjabi", "North Indian", "South Indian", "Chinese",
    "Italian", "Mughlai", "Street Food", "Fast Food", "Cafe", "Jain",
]

LOCATION_ALIASES = {
    "koramangala": "Bengaluru",
    "indiranagar": "Bengaluru",
    "bangalore": "Bengaluru",
}

CUISINE_ALIASES = {
    "chinese food": "Chinese",
    "indo chinese": "Chinese",
    "indo-chinese": "Chinese",
    "punjabi food": "Punjabi",
    "north indian food": "North Indian",
    "south indian food": "South Indian",
    "italian food": "Italian",
    "mughlai food": "Mughlai",
}

GREETING_RE = re.compile(
    r"^\s*(hi+|hello+|hey+|howdy|namaste|namaskar|"
    r"sat\s+sri\s+akal|good\s+(morning|afternoon|evening|day))"
    r"(?:\b|[!.?,\s]|$)",
    re.I,
)

CAPABILITY_RE = re.compile(
    r"\b(what\s+can\s+you\s+do|what\s+do\s+you\s+do|"
    r"how\s+do\s+you\s+work|help|capabilities|features|"
    r"tell\s+me\s+about\s+yourself)\b",
    re.I,
)

HUNGRY_RE = re.compile(
    r"^\s*(i'?m\s+hungry|i\s+am\s+hungry|feeling\s+hungry|"
    r"starving|i\s+want\s+to\s+eat|i\s+need\s+food)\s*[!.?]*$",
    re.I,
)


def _event(event_id: str, kind: str, label: str, detail: str,
           status: str = "complete") -> dict[str, str]:
    return {"id": event_id, "kind": kind, "label": label,
            "detail": detail, "status": status}


def _trace(step: int, title: str, type_: str, detail: str,
           tool: str | None = None,
           arguments: dict[str, Any] | None = None,
           result: str | None = None) -> dict[str, Any]:
    return {
        "step": step, "title": title, "type": type_, "detail": detail,
        "tool": tool, "arguments": arguments, "result": result,
    }


def _classify_intent(message: str) -> str:
    text = message.strip()
    if GREETING_RE.match(text):
        return "greeting"
    if CAPABILITY_RE.search(text):
        return "capability"
    if HUNGRY_RE.match(text):
        return "hungry"
    return "food"


def _memory_summary(memory: dict[str, Any]) -> str:
    labels = {
        "diet": "diet",
        "preferredCuisine": "cuisine",
        "dislikedCuisine": "dislikedCuisine",
        "spicePreference": "spicePreference",
        "budget": "budget",
        "location": "location",
    }
    parts = []
    for key, label in labels.items():
        value = memory.get(key)
        if value not in (None, "", [], {}):
            if key == "budget":
                try:
                    value = f"₹{int(float(value))}"
                except (TypeError, ValueError):
                    pass
            parts.append(f"{label}: {value}")
    return " + ".join(parts) if parts else "No preferences stored yet."


def _normalise(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().casefold())


def _canonical_cuisine(value: str) -> str | None:
    cleaned = _normalise(value)
    if cleaned in CUISINE_ALIASES:
        return CUISINE_ALIASES[cleaned]
    for cuisine in CUISINES:
        if cleaned == cuisine.casefold():
            return cuisine
    return None


def _detect_city(text: str) -> str | None:
    for city in CITIES:
        if re.search(rf"\b{re.escape(city)}\b", text, re.I):
            return city

    for alias, city in LOCATION_ALIASES.items():
        if re.search(rf"\b{re.escape(alias)}\b", text, re.I):
            return city

    match = re.search(
        r"\b(?:in|near|around|at)\s+([a-z][a-z -]{2,30})",
        text, re.I,
    )
    if match:
        candidate = re.split(
            r"\b(?:under|below|within|for|tonight|today|now|with|and)\b",
            match.group(1), maxsplit=1, flags=re.I,
        )[0].strip(" ,.")
        if candidate:
            return LOCATION_ALIASES.get(
                candidate.casefold(), candidate.title()
            )
    return None


def _detect_cuisine(text: str) -> str | None:
    matches: list[tuple[int, str]] = []

    for cuisine in CUISINES:
        if re.search(rf"\b{re.escape(cuisine)}\b", text, re.I):
            matches.append((len(cuisine), cuisine))

    for alias, cuisine in CUISINE_ALIASES.items():
        if re.search(rf"\b{re.escape(alias)}\b", text, re.I):
            matches.append((len(alias), cuisine))

    return max(matches, default=(0, None))[1]


def _detect_budget(text: str) -> float | None:
    patterns = [
        r"(?:under|below|less\s+than|up\s+to|upto|within)\s*₹?\s*(\d{2,6})",
        r"(?:₹|rs\.?|inr)\s*(\d{2,6})",
        r"budget\s*(?:of|is|around|:)??\s*₹?\s*(\d{2,6})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            amount = float(match.group(1))
            if 20 <= amount <= 100000:
                return amount
    return None


def _extract_diet(text: str) -> str | None:
    if re.search(r"\b(non[- ]?vegetarian|non[- ]?veg|nonveg)\b", text, re.I):
        return "non-vegetarian"
    if re.search(r"\bvegan\b", text, re.I):
        return "vegan-friendly"
    if re.search(r"\bjain\b", text, re.I):
        return "Jain-friendly"
    if re.search(r"\bvegetarian\b|\bveg\b", text, re.I):
        return "vegetarian"
    return None


def _negative_spice(text: str) -> bool:
    patterns = [
        r"\b(?:don't|do not|dont|dislike|hate|avoid)\s+"
        r"(?:like\s+)?(?:very\s+|too\s+|much\s+)?spicy\b",
        r"\bnot\s+too\s+spicy\b",
        r"\b(?:less|little)\s+spice\b",
        r"\b(?:no|without)\s+(?:very\s+|too\s+)?spice\b",
        r"\bnon[- ]?spicy\b",
    ]
    return any(re.search(p, text, re.I) for p in patterns)


def _positive_spice(text: str) -> bool:
    if _negative_spice(text):
        return False
    return bool(re.search(
        r"\b(?:spicy|spice|hot|fiery)\b", text, re.I
    ))


def _extract_disliked_cuisine(text: str) -> str | None:
    for cuisine in sorted(CUISINES, key=len, reverse=True):
        if re.search(
            r"(?:don't\s+like|do\s+not\s+like|dont\s+like|"
            r"dislike|hate|avoid|don't\s+want)"
            rf".{{0,35}}\b{re.escape(cuisine)}\b",
            text, re.I,
        ):
            return cuisine
    return None


def _extract_preferences(
    message: str, existing: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    text = message.casefold()
    updated = dict(existing)
    detected: dict[str, Any] = {}

    diet = _extract_diet(text)
    if diet:
        detected["diet"] = diet

    disliked = _extract_disliked_cuisine(text)
    cuisine = _detect_cuisine(text)

    if disliked:
        detected["dislikedCuisine"] = disliked
        if existing.get("preferredCuisine", "").casefold() == disliked.casefold():
            detected["preferredCuisine"] = None
    elif cuisine:
        detected["preferredCuisine"] = cuisine

    if _negative_spice(text):
        detected["spicePreference"] = "mild"
    elif _positive_spice(text):
        detected["spicePreference"] = "spicy"

    budget = _detect_budget(text)
    if budget is not None:
        detected["budget"] = budget

    city = _detect_city(text)
    if city:
        detected["location"] = city

    for key, value in detected.items():
        if value is None:
            updated.pop(key, None)
        else:
            updated[key] = value

    return updated, detected


def _diet_compatible(
    restaurant: dict[str, Any], diet: str | None
) -> bool:
    if not diet:
        return True

    labels = {str(x).casefold() for x in restaurant.get("diet", [])}

    if diet == "vegetarian":
        return "vegetarian" in labels or "vegan-friendly" in labels
    if diet == "vegan-friendly":
        return "vegan-friendly" in labels
    if diet == "jain-friendly":
        return "jain-friendly" in labels
    if diet == "non-vegetarian":
        return "non-vegetarian" in labels
    return True


def _cuisine_matches(
    restaurant: dict[str, Any], cuisine: str | None
) -> bool:
    if not cuisine:
        return True
    return cuisine.casefold() in {
        str(x).casefold() for x in restaurant.get("cuisine", [])
    }


def _spice_score(
    restaurant: dict[str, Any], preference: str | None
) -> float:
    if not preference:
        return 0.70

    level = str(restaurant.get("spice_level", "")).casefold()

    if preference == "spicy":
        return {"high": 1.0, "medium": 0.65, "low": 0.20}.get(level, 0.35)

    if preference == "mild":
        return {"low": 1.0, "medium": 0.65, "high": 0.15}.get(level, 0.35)

    return 0.70


def _rank(
    restaurants: list[dict[str, Any]],
    preferences: dict[str, Any],
) -> list[dict[str, Any]]:
    cuisine = preferences.get("preferredCuisine")
    budget = preferences.get("budget")
    spice = preferences.get("spicePreference")
    diet = preferences.get("diet")

    ranked = []

    for restaurant in restaurants:
        rating = float(restaurant.get("rating", 0) or 0)
        price = float(restaurant.get("average_price", 0) or 0)
        distance = float(restaurant.get("distance_km", 0) or 0)

        cuisine_score = (
            1.0 if cuisine and _cuisine_matches(restaurant, cuisine)
            else 0.55 if not cuisine else 0.20
        )

        if budget:
            budget_score = 1.0 if price <= float(budget) else max(
                0.0, 1.0 - min((price / float(budget)) - 1.0, 1.0)
            )
        else:
            budget_score = 0.70

        distance_score = max(0.0, 1.0 - distance / 10.0)
        taste_score = _spice_score(restaurant, spice)
        diet_score = 1.0 if diet else 0.70

        breakdown = {
            "cuisine": round(cuisine_score * 0.30, 3),
            "diet": round(diet_score * 0.30, 3),
            "rating": round((rating / 5) * 0.15, 3),
            "budget": round(budget_score * 0.10, 3),
            "taste": round(taste_score * 0.10, 3),
            "distance": round(distance_score * 0.05, 3),
        }

        score = round(sum(breakdown.values()) * 100, 1)

        reasons = []
        if cuisine:
            reasons.append(f"matches your {cuisine} preference")
        if diet:
            reasons.append(f"is compatible with a {diet} diet")
        reasons.append(f"has a {rating:.1f} rating")

        if budget and price <= float(budget):
            reasons.append(f"fits your ₹{int(float(budget))} budget")

        if spice:
            level = str(restaurant.get("spice_level", ""))
            if (
                spice == "spicy" and level.casefold() == "high"
            ) or (
                spice == "mild" and level.casefold() == "low"
            ):
                reasons.append(f"leans {level}-spice")

        reasons.append(f"it's only {distance:.1f} km away")

        reason = (
            "Recommended because it "
            + ", ".join(reasons[:-1])
            + f", and {reasons[-1]}."
        )

        ranked.append({
            **restaurant,
            "score": score,
            "reason": reason,
            "scoreBreakdown": breakdown,
        })

    return sorted(
        ranked,
        key=lambda x: (
            -float(x["score"]),
            -float(x.get("rating", 0)),
            float(x.get("distance_km", 0)),
        ),
    )


def _response(
    session_id: str,
    reply: str,
    memory: dict[str, Any],
    activity: list[dict[str, Any]],
    trace: list[dict[str, Any]],
    recommendations: list[dict[str, Any]],
    searched: int,
    after_cuisine: int,
    after_diet: int,
    started: float,
) -> dict[str, Any]:
    public = []

    for restaurant in recommendations:
        public.append({
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
        "recommendations": public,
        "stats": {
            "searched": searched,
            "afterCuisine": after_cuisine,
            "afterDiet": after_diet,
            "elapsedMs": max(
                1, round((time.perf_counter() - started) * 1000)
            ),
        },
    }


def _conversation(
    session_id: str, intent: str, message: str, started: float
) -> dict[str, Any]:
    memory = get_memory(session_id)

    if intent == "greeting":
        reply = (
            "Hi there! 👋 I'm LocalFood AI — your local food recommender. "
            "Tell me your city, preferred cuisine, or dietary needs and I'll "
            "find the best options for you. Try: "
            "I'm vegetarian and I want Punjabi food in Jalandhar."
        )
        label = "Greeting"
        detail = "Recognised a greeting — no restaurant search needed."

    elif intent == "capability":
        reply = (
            "Here's what I can do:\n\n"
            "🔍 **find_restaurants(city)** — searches the local restaurant index\n"
            "🍽️ **filter_by_cuisine(type)** — narrows results by cuisine\n"
            "🧠 **Memory** — remembers diet, cuisine, spice, budget and location\n"
            "🛡️ **Dietary guardrail** — removes incompatible restaurants\n"
            "🚫 **Dislike guardrail** — excludes cuisines you explicitly reject\n"
            "📊 **Ranking** — scores safe results using multiple signals"
        )
        label = "Capability query"
        detail = "Returned capabilities without unnecessary restaurant tool calls."

    else:
        reply = (
            "I can help with that! Which city are you in? "
            "You can also tell me your cuisine, diet, spice level, or budget."
        )
        label = "Hunger signal"
        detail = "The user is hungry but has not supplied enough search context."

    activity = [
        _event("understand", "thought", "Understanding your request", detail),
        _event("intent", "decision", label, "No restaurant tools needed."),
    ]
    trace = [
        _trace(1, "Intent", "intent",
                f'User said: "{message}" — classified as {intent}.'),
        _trace(2, "Decision", "decision",
                "Agent selected a conversational response."),
    ]

    return _response(
        session_id, reply, memory, activity, trace,
        [], 0, 0, 0, started
    )


def run_agent(session_id: str, message: str) -> dict[str, Any]:
    """Execute LocalFood AI's Plan → Act → Observe → Decide loop."""
    started = time.perf_counter()
    message = message.strip()

    intent = _classify_intent(message)
    if intent in ("greeting", "capability", "hungry"):
        return _conversation(session_id, intent, message, started)

    memory_before = get_memory(session_id)
    memory, detected = _extract_preferences(message, memory_before)

    activity = [
        _event(
            "understand", "thought", "Understanding your request",
            "Parsing the latest message and retrieving remembered preferences.",
        ),
        _event(
            "memory", "observation", "Memory read",
            _memory_summary(memory_before),
        ),
    ]

    trace = [
        _trace(
            1, "Intent", "intent",
            f'User asked: "{message}" — entering the food agent loop.',
        ),
        _trace(
            2, "Memory", "memory",
            f"Read memory: {_memory_summary(memory_before)}",
        ),
    ]

    # A remembered dietary hard constraint cannot be silently overridden.
    if (
        memory_before.get("diet") == "vegetarian"
        and detected.get("diet") == "non-vegetarian"
    ):
        activity.append(_event(
            "conflict", "warning", "Dietary conflict detected",
            "The latest request conflicts with the remembered vegetarian requirement.",
        ))
        trace.append(_trace(
            3, "Safety check", "decision",
            "Stopped before search because a hard dietary constraint conflicts.",
        ))
        return _response(
            session_id,
            "I noticed a conflict: your remembered preference is vegetarian, "
            "but this turn asks for non-vegetarian food. I haven't recommended "
            "anything yet. Tell me if you'd like to change your dietary preference.",
            memory_before, activity, trace, [], 0, 0, 0, started,
        )

    if detected:
        memory = save_memory(session_id, memory)
        changes = []
        names = {
            "preferredCuisine": "cuisine",
            "dislikedCuisine": "disliked cuisine",
            "spicePreference": "spice preference",
        }
        for key, value in detected.items():
            name = names.get(key, key)
            changes.append(
                f"cleared {name}" if value is None else f"{name} = {value}"
            )

        activity.append(_event(
            "memory-write", "decision", "Memory updated",
            "Remembering " + ", ".join(changes) + ".",
        ))
        trace.append(_trace(
            3, "Memory write", "memory",
            f"Updated preferences: {detected}",
        ))
    else:
        memory = save_memory(session_id, memory)

    city = memory.get("location")
    cuisine = memory.get("preferredCuisine")
    disliked = memory.get("dislikedCuisine")
    diet = memory.get("diet")

    if cuisine and disliked and cuisine.casefold() == disliked.casefold():
        memory.pop("preferredCuisine", None)
        cuisine = None
        memory = save_memory(session_id, memory)
        activity.append(_event(
            "preference-conflict", "warning", "Cuisine conflict resolved",
            f"The explicit dislike of {disliked} overrides the older positive preference.",
        ))

    if not city:
        activity.append(_event(
            "clarify", "decision", "Need one detail",
            "A city is required before searching the restaurant index.",
        ))
        trace.append(_trace(
            4, "Next action", "decision",
            "Ask for city instead of guessing.",
        ))
        return _response(
            session_id,
            "Got it — I'll remember those preferences. Which city should I search in?",
            memory, activity, trace, [], 0, 0, 0, started,
        )

    plan = [f"search {city}"]
    if cuisine:
        plan.append(f"filter {cuisine}")
    if disliked:
        plan.append(f"exclude {disliked}")
    if diet:
        plan.append(f"enforce {diet}")
    plan.append("rank safe options")

    activity.append(_event(
        "plan", "decision", "Plan formed",
        " → ".join(plan).capitalize() + ".",
    ))
    trace.append(_trace(
        4, "Plan", "plan",
        " → ".join(plan),
    ))

    # ACT: city search.
    try:
        activity.append(_event(
            "find-call", "tool", "Calling find_restaurants()",
            f"Searching the local index for {city}.",
        ))
        trace.append(_trace(
            5, "Tool Call", "tool",
            "Searching because a valid city is available.",
            "find_restaurants", {"city": city},
        ))

        search_results = find_restaurants(city)
        trace[-1]["result"] = f"{len(search_results)} restaurants found"

        activity.append(_event(
            "find-result", "observation", "Restaurant search complete",
            f"Found {len(search_results)} restaurants in {city}.",
        ))
        trace.append(_trace(
            6, "Tool Result", "observation",
            f"find_restaurants returned {len(search_results)} records.",
            result=f"{len(search_results)} restaurants found",
        ))

    except Exception:
        activity.append(_event(
            "tool-error", "warning", "Search temporarily failed",
            "The tool reported an error; no result was fabricated.",
        ))
        trace.append(_trace(
            6, "Tool Result", "observation",
            "find_restaurants raised an error.",
            "find_restaurants", {"city": city}, "Tool error",
        ))
        return _response(
            session_id,
            "Restaurant search temporarily failed. Please try again.",
            memory, activity, trace, [], 0, 0, 0, started,
        )

    if not search_results:
        activity.append(_event(
            "no-results", "warning", "No restaurants found",
            f"The dataset has no entries for {city}.",
        ))
        return _response(
            session_id,
            f"I couldn't find restaurants in {city}. Try Jalandhar, Phagwara, "
            "Ludhiana, Amritsar, Chandigarh, Delhi, or Bengaluru.",
            memory, activity, trace, [], 0, 0, 0, started,
        )

    # ACT: cuisine filter. tools.py deliberately filters the previous search.
    cuisine_results = list(search_results)

    if cuisine:
        activity.append(_event(
            "cuisine-call", "tool", "Calling filter_by_cuisine()",
            f"Narrowing the observation to {cuisine}.",
        ))
        trace.append(_trace(
            7, "Tool Call", "tool",
            "Cuisine was explicitly requested, so the previous observation "
            "is filtered before ranking.",
            "filter_by_cuisine", {"type": cuisine},
        ))

        try:
            cuisine_results = filter_by_cuisine(cuisine)
        except Exception:
            activity.append(_event(
                "cuisine-error", "warning", "Cuisine filter failed",
                "No filtered result was fabricated.",
            ))
            return _response(
                session_id,
                "Cuisine filtering temporarily failed. Please try again.",
                memory, activity, trace, [], len(search_results), 0, 0, started,
            )

        # Defensive locality check.
        city_key = str(city).casefold()
        cuisine_results = [
            r for r in cuisine_results
            if str(r.get("city", "")).casefold() == city_key
        ]

        if not cuisine_results:
            cuisine_results = [
                r for r in search_results
                if _cuisine_matches(r, cuisine)
            ]

        trace[-1]["result"] = f"{len(cuisine_results)} cuisine matches"
        activity.append(_event(
            "cuisine-result", "observation", "Cuisine filter complete",
            f"Found {len(cuisine_results)} {cuisine} matches in {city}.",
        ))

    # HARD EXCLUSION: disliked cuisine.
    if disliked:
        before = len(cuisine_results)
        cuisine_results = [
            r for r in cuisine_results
            if disliked.casefold() not in {
                str(x).casefold() for x in r.get("cuisine", [])
            }
        ]
        activity.append(_event(
            "dislike-filter", "decision", "Applying cuisine exclusion",
            f"Removed {before - len(cuisine_results)} option(s) matching disliked cuisine {disliked}.",
        ))
        trace.append(_trace(
            9, "Dislike Guardrail", "filter",
            f"Explicitly excluded {disliked}. {len(cuisine_results)} remain.",
        ))

    # HARD GUARDRAIL: diet.
    before_diet = len(cuisine_results)
    safe_results = [
        r for r in cuisine_results
        if _diet_compatible(r, diet)
    ]

    activity.append(_event(
        "diet-filter", "decision", "Applying dietary guardrail",
        f"Kept {len(safe_results)} options; removed "
        f"{before_diet - len(safe_results)} incompatible option(s).",
    ))
    trace.append(_trace(
        10, "Dietary Guardrail", "filter",
        f"Applied hard dietary requirement: {diet or 'none'}. "
        f"{len(safe_results)} remain.",
    ))

    if not safe_results:
        constraints = []
        if cuisine:
            constraints.append(cuisine)
        if disliked:
            constraints.append(f"excluding {disliked}")
        if diet:
            constraints.append(f"satisfying {diet}")

        description = " and ".join(constraints) or "your active preferences"

        activity.append(_event(
            "no-safe-match", "warning", "No safe match",
            "Hard constraints are respected; incompatible options are not recommended.",
        ))
        trace.append(_trace(
            11, "Final Recommendation", "result",
            "No safe recommendation exists after hard constraints.",
        ))

        return _response(
            session_id,
            f"I found restaurants in {city}, but none matched {description}.",
            memory, activity, trace, [],
            len(search_results), len(cuisine_results), 0, started,
        )

    # DECIDE: rank only safe candidates.
    ranked = _rank(safe_results, memory)

    activity.append(_event(
        "rank", "decision", "Ranking remaining options",
        "Scoring safe candidates using cuisine, diet, rating, budget, taste, and distance.",
    ))
    activity.append(_event(
        "ready", "success", "Recommendation ready",
        f"Ranked {len(ranked)} safe match(es).",
    ))
    trace.append(_trace(
        11, "Ranking", "decision",
        "All hard constraints were enforced before ranking.",
    ))
    trace.append(_trace(
        12, "Final Recommendation", "result",
        "Returned ranked safe candidates with transparent score breakdowns.",
    ))

    best = ranked[0]
    count_word = "match" if len(ranked) == 1 else "matches"

    return _response(
        session_id,
        f"I found {len(ranked)} safe {count_word} in {city}. "
        f"{best['name']} is the strongest overall fit at {best['score']}/100.",
        memory, activity, trace, ranked[:5],
        len(search_results), len(cuisine_results), len(safe_results), started,
    )
