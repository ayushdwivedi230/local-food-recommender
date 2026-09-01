"""Enhanced LocalFood AI agent with improved state management, NLU, and ranking.

This agent demonstrates an explicit Plan → Act → Observe → Decide loop.
It maintains clear state separation between hard constraints (diet, dislikes)
and soft preferences (cuisine, budget, spice). All preferences are stored
without using None, preventing "your None requirement" type errors.
"""

from __future__ import annotations

import re
import time
from datetime import datetime, timezone
from typing import Any
from dataclasses import dataclass, field, asdict
from enum import Enum

from memory import get_memory, save_memory
from tools import filter_by_cuisine, find_restaurants


# ============================================================================
# CONSTANTS & CONFIGURATION
# ============================================================================

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
    "bengaluru": "Bengaluru",
}

CUISINE_ALIASES = {
    "chinese food": "Chinese",
    "indo chinese": "Chinese",
    "indo-chinese": "Chinese",
    "punjabi food": "Punjabi",
    "punjabi": "Punjabi",
    "north indian food": "North Indian",
    "north indian": "North Indian",
    "south indian food": "South Indian",
    "south indian": "South Indian",
    "italian food": "Italian",
    "italian": "Italian",
    "mughlai food": "Mughlai",
    "mughlai": "Mughlai",
    "street food": "Street Food",
    "fast food": "Fast Food",
    "cafe": "Cafe",
    "coffee": "Cafe",
    "jain food": "Jain",
    "jain": "Jain",
}

# Regex patterns for intent detection
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


# ============================================================================
# STATE CLASSES
# ============================================================================

class DietType(Enum):
    """Dietary requirements - hard constraints."""
    VEGETARIAN = "vegetarian"
    VEGAN = "vegan-friendly"
    JAIN = "Jain-friendly"
    NON_VEGETARIAN = "non-vegetarian"


class SpiceLevel(Enum):
    """Spice preferences."""
    MILD = "mild"
    MEDIUM = "medium"
    SPICY = "spicy"


class BudgetType(Enum):
    """Budget constraint type."""
    HARD = "hard"  # "under ₹500"
    SOFT = "soft"  # "around ₹500"


@dataclass
class PreferenceState:
    """Explicit state representation - no None values exposed to user."""
    
    # Hard constraints (must not be violated)
    diet: DietType | None = None
    disliked_cuisines: set[str] = field(default_factory=set)
    
    # Soft preferences
    preferred_cuisine: str | None = None
    spice_level: SpiceLevel | None = None
    budget: float | None = None
    budget_type: BudgetType = BudgetType.SOFT
    
    # Location (required for search)
    location: str | None = None
    
    def to_memory(self) -> dict[str, Any]:
        """Convert to memory format (backward compatible)."""
        return {
            "diet": self.diet.value if self.diet else None,
            "dislikedCuisine": list(self.disliked_cuisines)[0] if len(self.disliked_cuisines) == 1 else None,
            "dislikedCuisines": sorted(list(self.disliked_cuisines)) if self.disliked_cuisines else None,
            "preferredCuisine": self.preferred_cuisine,
            "spicePreference": self.spice_level.value if self.spice_level else None,
            "budget": self.budget,
            "location": self.location,
        }
    
    @staticmethod
    def from_memory(mem: dict[str, Any]) -> PreferenceState:
        """Load from memory (backward compatible)."""
        state = PreferenceState()
        
        if mem.get("diet"):
            for dt in DietType:
                if dt.value == mem.get("diet"):
                    state.diet = dt
                    break
        
        # Support both single dislike and multiple
        if mem.get("dislikedCuisine"):
            state.disliked_cuisines.add(mem["dislikedCuisine"])
        if mem.get("dislikedCuisines"):
            state.disliked_cuisines.update(mem["dislikedCuisines"])
        
        state.preferred_cuisine = mem.get("preferredCuisine")
        
        if mem.get("spicePreference"):
            for sl in SpiceLevel:
                if sl.value == mem.get("spicePreference"):
                    state.spice_level = sl
                    break
        
        state.budget = mem.get("budget")
        state.location = mem.get("location")
        
        return state


# ============================================================================
# HELPER FUNCTIONS: Normalization
# ============================================================================

def _normalise(value: str) -> str:
    """Normalize text for comparison."""
    return re.sub(r"\s+", " ", value.strip().casefold())


def _canonical_cuisine(value: str) -> str | None:
    """Return canonical cuisine name or None."""
    cleaned = _normalise(value)
    if cleaned in CUISINE_ALIASES:
        return CUISINE_ALIASES[cleaned]
    for cuisine in CUISINES:
        if cleaned == cuisine.casefold():
            return cuisine
    return None


# ============================================================================
# HELPER FUNCTIONS: Entity Detection
# ============================================================================

def _detect_city(text: str) -> str | None:
    """Detect city from text, using aliases and patterns."""
    # Direct match against known cities
    for city in CITIES:
        if re.search(rf"\b{re.escape(city)}\b", text, re.I):
            return city
    
    # Check aliases
    for alias, city in LOCATION_ALIASES.items():
        if re.search(rf"\b{re.escape(alias)}\b", text, re.I):
            return city
    
    # Contextual pattern: "in City", "near City", etc.
    match = re.search(
        r"\b(?:in|near|around|at|visiting|currently\s+(?:in|at))\s+"
        r"([a-z][a-z\s-]{1,30})",
        text, re.I,
    )
    if match:
        candidate = re.split(
            r"\b(?:under|below|within|for|tonight|today|now|with|and|for)\b",
            match.group(1), maxsplit=1, flags=re.I,
        )[0].strip(" ,.")
        if candidate:
            return LOCATION_ALIASES.get(
                _normalise(candidate), candidate.title()
            )
    
    return None


def _detect_cuisine(text: str) -> str | None:
    """Detect preferred cuisine (greedy by length)."""
    matches: list[tuple[int, str]] = []
    
    for cuisine in CUISINES:
        if re.search(rf"\b{re.escape(cuisine)}\b", text, re.I):
            matches.append((len(cuisine), cuisine))
    
    for alias, cuisine in CUISINE_ALIASES.items():
        if re.search(rf"\b{re.escape(alias)}\b", text, re.I):
            matches.append((len(alias), cuisine))
    
    return max(matches, default=(0, None))[1]


def _detect_budget(text: str) -> tuple[float, BudgetType] | None:
    """Detect budget and type (hard vs soft constraint)."""
    # Hard budget: "under ₹500", "below 500", "within 300"
    hard_patterns = [
        r"(?:under|below|less\s+than|up\s+to|upto|within|max|maximum)\s*₹?\s*(\d{2,6})",
    ]
    for pattern in hard_patterns:
        match = re.search(pattern, text, re.I)
        if match:
            amount = float(match.group(1))
            if 20 <= amount <= 100000:
                return amount, BudgetType.HARD
    
    # Soft budget: "around ₹500", "budget of 500", "₹500"
    soft_patterns = [
        r"(?:around|approximately|approx|about|roughly)\s*₹?\s*(\d{2,6})",
        r"budget\s*(?:of|is|around|:)?\s*₹?\s*(\d{2,6})",
        r"(?:₹|rs\.?|inr)\s*(\d{2,6})",
    ]
    for pattern in soft_patterns:
        match = re.search(pattern, text, re.I)
        if match:
            amount = float(match.group(1))
            if 20 <= amount <= 100000:
                return amount, BudgetType.SOFT
    
    return None


# ============================================================================
# HELPER FUNCTIONS: Preference Extraction with Negation Awareness
# ============================================================================

def _extract_diet(text: str) -> DietType | None:
    """Extract dietary preference, with negation awareness."""
    text = _normalise(text)
    
    # Check for non-vegetarian first (more specific)
    if re.search(r"\b(non[- ]?vegetarian|non[- ]?veg|nonveg|meat|eggs?)\b", text):
        # But make sure it's not negated
        if not re.search(
            r"\b(?:no|without|don't\s+(?:want|like)|don't\s+eat)\s+"
            r"(?:non[- ]?(?:veg|vegetarian)|meat|eggs?)\b",
            text
        ):
            return DietType.NON_VEGETARIAN
    
    # Check for vegan
    if re.search(r"\bvegan\b", text):
        if not re.search(r"\b(?:not|no|don't|don't\s+want)\s+vegan\b", text):
            return DietType.VEGAN
    
    # Check for Jain
    if re.search(r"\bjain\b", text):
        if not re.search(r"\b(?:not|no|don't|don't\s+want)\s+jain\b", text):
            return DietType.JAIN
    
    # Check for vegetarian (least specific, check last)
    if re.search(r"\b(?:vegetarian|veg|i'm\s+veg)\b", text):
        if not re.search(
            r"\b(?:no|not|without|don't\s+(?:want|like)|stop\s+being)\s+"
            r"(?:vegetarian|veg)\b",
            text
        ):
            return DietType.VEGETARIAN
    
    return None


def _detect_disliked_cuisines(text: str) -> set[str]:
    """Detect cuisines the user explicitly dislikes."""
    disliked = set()
    
    # Pattern: "don't like X", "avoid X", "not X", "exclude X"
    for cuisine in sorted(CUISINES, key=len, reverse=True):
        pattern = (
            r"(?:don't\s+like|do\s+not\s+like|dont\s+like|"
            r"dislike|hate|avoid|don't\s+want|exclude|"
            r"anything\s+but|everything\s+except|no|without)"
            rf".{{0,40}}\b{re.escape(cuisine)}\b"
        )
        if re.search(pattern, text, re.I):
            disliked.add(cuisine)
    
    return disliked


def _extract_spice_preference(text: str) -> SpiceLevel | None:
    """Extract spice preference, correctly handling negation."""
    text = _normalise(text)

    # Explicit negative patterns: "don't like spicy", "not spicy", "don't like too much spice".
    negative_patterns = [
        r"\b(?:don't|do\s+not|dont|dislike|hate|avoid)\s+"
        r"(?:like\s+)?(?:very\s+|too\s+|much\s+|too\s+much\s+)?(?:spicy|spice)\b",
        r"\b(?:no|without)\s+(?:very\s+|too\s+)?(?:spice|spicy)\b",
        r"\bnot\s+too\s+(?:spicy|spice)\b",
        r"\b(?:less|little|low|mild)\s+(?:spice|spicy)\b",
        r"\bnon[- ]?spicy\b",
        r"\b(?:don't\s+want|prefer)\s+(?:spicy|spice)\b",
    ]

    for pattern in negative_patterns:
        if re.search(pattern, text, re.I):
            return SpiceLevel.MILD

    # Explicit positive patterns
    if re.search(r"\b(?:spicy|spice|very\s+spicy|too\s+spicy|hot|fiery)\b", text, re.I):
        return SpiceLevel.SPICY

    # Medium is rarely expressed; treat "medium spice" if found
    if re.search(r"\bmedium\s+(?:spice|spicy)\b", text, re.I):
        return SpiceLevel.MEDIUM

    return None


# ============================================================================
# HELPER FUNCTIONS: Preference Updates & Conflict Detection
# ============================================================================

def _extract_preferences(
    message: str, existing_state: PreferenceState
) -> tuple[PreferenceState, dict[str, Any]]:
    """Extract new preferences from message and merge with existing state.
    
    Returns:
        (merged_state, changes_dict) - the merged state and what was changed
    """
    text = message.casefold()
    updated = PreferenceState(
        diet=existing_state.diet,
        disliked_cuisines=set(existing_state.disliked_cuisines),
        preferred_cuisine=existing_state.preferred_cuisine,
        spice_level=existing_state.spice_level,
        budget=existing_state.budget,
        budget_type=existing_state.budget_type,
        location=existing_state.location,
    )
    
    changes: dict[str, Any] = {}
    
    # Extract new diet
    new_diet = _extract_diet(text)
    if new_diet:
        if existing_state.diet and existing_state.diet != new_diet:
            changes["diet_changed_from"] = existing_state.diet.value
        changes["diet"] = new_diet.value
        updated.diet = new_diet
    
    # Extract disliked cuisines
    new_disliked = _detect_disliked_cuisines(text)
    if new_disliked:
        changes["disliked_cuisines"] = sorted(list(new_disliked))
        # Disliked overrides preferred if they conflict
        if updated.preferred_cuisine in new_disliked:
            changes["cleared_preferred_cuisine"] = updated.preferred_cuisine
            updated.preferred_cuisine = None
        updated.disliked_cuisines = new_disliked
    
    # Extract preferred cuisine
    new_cuisine = _detect_cuisine(text)
    if new_cuisine:
        if new_cuisine not in new_disliked:  # Don't prefer a disliked cuisine
            if existing_state.preferred_cuisine and existing_state.preferred_cuisine != new_cuisine:
                changes["cuisine_changed_from"] = existing_state.preferred_cuisine
            changes["preferred_cuisine"] = new_cuisine
            updated.preferred_cuisine = new_cuisine
    
    # Extract spice preference
    new_spice = _extract_spice_preference(text)
    if new_spice:
        if existing_state.spice_level and existing_state.spice_level != new_spice:
            changes["spice_changed_from"] = existing_state.spice_level.value
        changes["spice_level"] = new_spice.value
        updated.spice_level = new_spice
    
    # Extract budget
    budget_result = _detect_budget(text)
    if budget_result:
        amount, btype = budget_result
        if existing_state.budget and abs(existing_state.budget - amount) > 1:
            changes["budget_changed_from"] = existing_state.budget
        changes["budget"] = amount
        changes["budget_type"] = btype.value
        updated.budget = amount
        updated.budget_type = btype
    
    # Extract location
    new_location = _detect_city(text)
    if new_location:
        if existing_state.location and existing_state.location != new_location:
            changes["location_changed_from"] = existing_state.location
        changes["location"] = new_location
        updated.location = new_location
    
    return updated, changes


def _detect_dietary_conflict(old: PreferenceState, new: PreferenceState) -> str | None:
    """Detect dietary conflicts (e.g., veg → non-veg) and return explanation or None."""
    if old.diet and new.diet and old.diet != new.diet:
        return (
            f"Your remembered preference is {old.diet.value}, "
            f"but this turn asks for {new.diet.value}. "
            f"This is a significant change. Please confirm."
        )
    return None


# ============================================================================
# HELPER FUNCTIONS: Filtering & Compatibility
# ============================================================================

def _diet_compatible(restaurant: dict[str, Any], diet: DietType | None) -> bool:
    """Check if restaurant is compatible with dietary requirement (hard constraint)."""
    if not diet:
        return True
    
    labels = {str(x).casefold() for x in restaurant.get("diet", [])}
    
    if diet == DietType.VEGETARIAN:
        return "vegetarian" in labels or "vegan-friendly" in labels or "jain-friendly" in labels
    if diet == DietType.VEGAN:
        return "vegan-friendly" in labels
    if diet == DietType.JAIN:
        return "jain-friendly" in labels
    if diet == DietType.NON_VEGETARIAN:
        return "non-vegetarian" in labels
    
    return True


def _cuisine_matches(restaurant: dict[str, Any], cuisine: str | None) -> bool:
    """Check if restaurant's cuisine matches preferred cuisine."""
    if not cuisine:
        return True
    return cuisine.casefold() in {
        str(x).casefold() for x in restaurant.get("cuisine", [])
    }


def _is_disliked_cuisine(restaurant: dict[str, Any], disliked: set[str]) -> bool:
    """Check if restaurant has a disliked cuisine (hard constraint)."""
    if not disliked:
        return False
    
    rest_cuisines = {str(x).casefold() for x in restaurant.get("cuisine", [])}
    disliked_normalized = {str(x).casefold() for x in disliked}
    
    return bool(rest_cuisines & disliked_normalized)


# ============================================================================
# HELPER FUNCTIONS: Scoring & Ranking
# ============================================================================

def _spice_score(restaurant: dict[str, Any], preference: SpiceLevel | None) -> float:
    """Score restaurant's spice level against preference."""
    if not preference:
        return 0.70  # Neutral when no preference
    
    level = str(restaurant.get("spice_level", "")).casefold()
    
    if preference == SpiceLevel.SPICY:
        return {"high": 1.0, "medium": 0.65, "low": 0.20}.get(level, 0.35)
    
    if preference == SpiceLevel.MILD:
        return {"low": 1.0, "medium": 0.65, "high": 0.15}.get(level, 0.35)
    
    if preference == SpiceLevel.MEDIUM:
        return {"medium": 1.0, "high": 0.65, "low": 0.65}.get(level, 0.35)
    
    return 0.70


def _budget_fit_score(
    restaurant_price: float,
    budget: float | None,
    budget_type: BudgetType
) -> float:
    """Score restaurant's price against budget constraint."""
    if budget is None:
        return 0.70  # Neutral when no budget preference
    
    if budget_type == BudgetType.HARD:
        # Hard constraint: under budget should score high, over should score low
        if restaurant_price <= budget:
            return 1.0
        else:
            # Penalize overages, but don't zero them out
            ratio = restaurant_price / budget
            return max(0.1, 1.0 - min((ratio - 1.0) * 0.5, 0.8))
    else:
        # Soft preference: "around" budget
        if restaurant_price <= budget:
            return max(0.8, 1.0 - (budget - restaurant_price) / (budget * 0.3))
        else:
            # Slightly penalize being over, but not too much
            ratio = restaurant_price / budget
            return max(0.5, 1.0 - min((ratio - 1.0) * 0.3, 0.4))


def _rank(
    restaurants: list[dict[str, Any]],
    preferences: PreferenceState,
) -> list[dict[str, Any]]:
    """Rank restaurants using transparent scoring based on preferences."""
    ranked = []
    
    for restaurant in restaurants:
        rating = float(restaurant.get("rating", 0) or 0)
        price = float(restaurant.get("average_price", 0) or 0)
        distance = float(restaurant.get("distance_km", 0) or 0)
        
        # Scoring components
        cuisine_score = (
            1.0 if preferences.preferred_cuisine and _cuisine_matches(restaurant, preferences.preferred_cuisine)
            else 0.55 if not preferences.preferred_cuisine
            else 0.25
        )
        
        budget_score = _budget_fit_score(price, preferences.budget, preferences.budget_type)
        distance_score = max(0.0, 1.0 - (distance / 10.0))
        spice_score = _spice_score(restaurant, preferences.spice_level)
        diet_score = 1.0  # Already filtered by hard constraint
        rating_score = rating / 5.0
        
        # Weighted breakdown
        breakdown = {
            "cuisine": round(cuisine_score * 0.30, 3),
            "diet": round(diet_score * 0.25, 3),
            "rating": round(rating_score * 0.20, 3),
            "budget": round(budget_score * 0.12, 3),
            "spice": round(spice_score * 0.08, 3),
            "distance": round(distance_score * 0.05, 3),
        }
        
        score = round(sum(breakdown.values()) * 100, 1)
        
        # Build reason based on actual preferences and scores
        reasons = []
        
        if preferences.preferred_cuisine:
            if _cuisine_matches(restaurant, preferences.preferred_cuisine):
                reasons.append(f"matches your {preferences.preferred_cuisine} preference")
            else:
                reasons.append(f"offers cuisine options despite {preferences.preferred_cuisine} not being primary")
        
        reasons.append(f"has a {rating:.1f} rating")
        
        if preferences.budget:
            if price <= preferences.budget:
                reasons.append(f"fits your ₹{int(preferences.budget)} budget")
            else:
                reasons.append(f"is ₹{int(price)} (slightly above your ₹{int(preferences.budget)} budget)")
        
        if preferences.spice_level:
            level = str(restaurant.get("spice_level", "")).casefold()
            if (preferences.spice_level == SpiceLevel.SPICY and level == "high") or \
               (preferences.spice_level == SpiceLevel.MILD and level == "low"):
                reasons.append(f"offers {level}-spice levels you prefer")
        
        reasons.append(f"is {distance:.1f} km away")
        
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


# ============================================================================
# HELPER FUNCTIONS: Tracing & Activity
# ============================================================================

def _event(event_id: str, kind: str, label: str, detail: str,
           status: str = "complete") -> dict[str, str]:
    """Create an activity event."""
    return {"id": event_id, "kind": kind, "label": label,
            "detail": detail, "status": status}


def _trace(step: int, title: str, type_: str, detail: str,
           tool: str | None = None,
           arguments: dict[str, Any] | None = None,
           result: str | None = None) -> dict[str, Any]:
    """Create a trace entry."""
    return {
        "step": step, "title": title, "type": type_, "detail": detail,
        "tool": tool, "arguments": arguments, "result": result,
    }


def _state_summary(state: PreferenceState) -> str:
    """Human-readable summary of current state preferences."""
    parts = []
    
    if state.diet:
        parts.append(f"diet: {state.diet.value}")
    
    if state.preferred_cuisine:
        parts.append(f"cuisine: {state.preferred_cuisine}")
    
    if state.disliked_cuisines:
        parts.append(f"no: {', '.join(sorted(state.disliked_cuisines))}")
    
    if state.spice_level:
        parts.append(f"spice: {state.spice_level.value}")
    
    if state.budget:
        budget_desc = "under ₹" if state.budget_type == BudgetType.HARD else "around ₹"
        parts.append(f"budget: {budget_desc}{int(state.budget)}")
    
    if state.location:
        parts.append(f"location: {state.location}")
    
    return " + ".join(parts) if parts else "No preferences stored."


# ============================================================================
# INTENT CLASSIFICATION
# ============================================================================

def _classify_intent(message: str) -> str:
    """Classify user intent."""
    text = message.strip()
    
    if GREETING_RE.match(text):
        return "greeting"
    
    if CAPABILITY_RE.search(text):
        return "capability"
    
    if HUNGRY_RE.match(text):
        return "hungry"
    
    return "food"


# ============================================================================
# RESPONSE BUILDING (Backward Compatible)
# ============================================================================

def _response(
    session_id: str,
    reply: str,
    state: PreferenceState,
    activity: list[dict[str, Any]],
    trace: list[dict[str, Any]],
    recommendations: list[dict[str, Any]],
    searched: int,
    after_cuisine: int,
    after_diet: int,
    started: float,
    memory_override: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build response in backward-compatible format while preserving complete memory."""
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

    memory_dict = dict(get_memory(session_id))
    memory_dict.update(state.to_memory())
    if memory_override:
        memory_dict.update(memory_override)
    if not isinstance(memory_dict.get("updatedAt"), str) or not memory_dict["updatedAt"]:
        memory_dict["updatedAt"] = datetime.now(timezone.utc).isoformat()

    return {
        "sessionId": session_id,
        "mode": "demo",
        "reply": reply,
        "memory": memory_dict,
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
    session_id: str, intent: str, message: str, state: PreferenceState, started: float
) -> dict[str, Any]:
    """Handle conversational (non-search) intents."""
    if intent == "greeting":
        reply = (
            "Hi there! 👋 I'm LocalFood AI — your local food recommender. "
            "Tell me your city, preferred cuisine, dietary needs, or budget and I'll "
            "find the best options for you. Try: "
            "'I'm vegetarian and I want Punjabi food in Jalandhar under ₹500.'"
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
            "📊 **Ranking** — scores safe results using rating, budget, taste, and distance"
        )
        label = "Capability query"
        detail = "Returned capabilities without unnecessary restaurant tool calls."
    
    else:  # intent == "hungry"
        if state.location:
            # They're hungry and we know the location; ask for cuisine/preference clarification
            reply = (
                f"You mentioned you're hungry and I remember you're in {state.location}. "
                f"What cuisine or type of food are you in the mood for?"
            )
            label = "Hunger signal with known location"
            detail = "The user is hungry; location is remembered."
        else:
            # They're hungry but we don't know the location
            reply = (
                "I can help with that! Which city are you in? "
                "You can also tell me your preferred cuisine, dietary needs, or budget."
            )
            label = "Hunger signal"
            detail = "The user is hungry but location is unknown."
    
    activity = [
        _event("understand", "thought", "Understanding your request", 
               f"Parsed message as {intent}."),
        _event("intent", "decision", label, "No restaurant tools needed."),
    ]
    trace = [
        _trace(1, "Intent", "intent",
               f'User said: "{message}" — classified as {intent}.'),
        _trace(2, "Decision", "decision",
               "Agent selected a conversational response."),
    ]
    
    return _response(
        session_id, reply, state, activity, trace,
        [], 0, 0, 0, started, memory_override=get_memory(session_id)
    )


# ============================================================================
# MAIN AGENT LOOP: Plan → Act → Observe → Decide
# ============================================================================

def run_agent(session_id: str, message: str) -> dict[str, Any]:
    """Execute the agent loop: PLAN → ACT → OBSERVE → DECIDE."""
    started = time.perf_counter()
    message = message.strip()
    
    # Intent classification
    intent = _classify_intent(message)
    
    # Handle conversational intents
    if intent in ("greeting", "capability", "hungry"):
        old_mem = get_memory(session_id)
        state = PreferenceState.from_memory(old_mem)
        return _conversation(session_id, intent, message, state, started)
    
    # ========== PLAN PHASE ==========
    old_mem = get_memory(session_id)
    old_state = PreferenceState.from_memory(old_mem)
    new_state, changes = _extract_preferences(message, old_state)
    
    activity = [
        _event(
            "understand", "thought", "Understanding your request",
            "Parsing the latest message and retrieving remembered preferences.",
        ),
        _event(
            "memory", "observation", "Memory read",
            _state_summary(old_state) if old_state.diet or old_state.preferred_cuisine or old_state.location 
            else "No preferences stored yet.",
        ),
    ]
    
    trace = [
        _trace(
            1, "Intent", "intent",
            f'User asked: "{message}" — entering the food agent loop.',
        ),
        _trace(
            2, "Memory", "memory",
            f"Read memory: {_state_summary(old_state)}",
        ),
    ]
    
    # Detect dietary conflict
    conflict_msg = _detect_dietary_conflict(old_state, new_state)
    if conflict_msg:
        activity.append(_event(
            "conflict", "warning", "Dietary conflict detected",
            conflict_msg,
        ))
        trace.append(_trace(
            3, "Safety check", "decision",
            "Stopped because a hard dietary constraint conflicts with the new request.",
        ))
        return _response(
            session_id,
            conflict_msg + " Would you like to change your dietary preference?",
            old_state, activity, trace, [], 0, 0, 0, started,
            memory_override=get_memory(session_id),
        )
    
    # Save new preferences
    if changes:
        saved_mem = save_memory(session_id, new_state.to_memory())
        new_state = PreferenceState.from_memory(saved_mem)

        changes_list = []
        if "diet" in changes:
            if "diet_changed_from" in changes:
                changes_list.append(f"changed diet from {changes['diet_changed_from']} to {changes['diet']}")
            else:
                changes_list.append(f"set diet = {changes['diet']}")
        
        if "preferred_cuisine" in changes:
            if "cuisine_changed_from" in changes:
                changes_list.append(f"changed cuisine from {changes['cuisine_changed_from']} to {changes['preferred_cuisine']}")
            else:
                changes_list.append(f"set cuisine = {changes['preferred_cuisine']}")
        
        if "disliked_cuisines" in changes:
            changes_list.append(f"dislike {', '.join(changes['disliked_cuisines'])}")
        
        if "spice_level" in changes:
            if "spice_changed_from" in changes:
                changes_list.append(f"changed spice from {changes['spice_changed_from']} to {changes['spice_level']}")
            else:
                changes_list.append(f"set spice = {changes['spice_level']}")
        
        if "budget" in changes:
            if "budget_changed_from" in changes:
                changes_list.append(f"changed budget from ₹{int(changes['budget_changed_from'])} to ₹{int(changes['budget'])}")
            else:
                changes_list.append(f"set budget = ₹{int(changes['budget'])}")
        
        if "location" in changes:
            if "location_changed_from" in changes:
                changes_list.append(f"changed location from {changes['location_changed_from']} to {changes['location']}")
            else:
                changes_list.append(f"set location = {changes['location']}")
        
        activity.append(_event(
            "memory-write", "decision", "Memory updated",
            "Remembering: " + ", ".join(changes_list) + ".",
        ))
        trace.append(_trace(
            3, "Memory write", "memory",
            f"Updated preferences: {changes}",
        ))
    else:
        saved_mem = save_memory(session_id, new_state.to_memory())
        new_state = PreferenceState.from_memory(saved_mem)
    
    # Check if we can proceed with search
    if not new_state.location:
        activity.append(_event(
            "clarify", "decision", "Need one detail",
            "A city is required before searching the restaurant index.",
        ))
        trace.append(_trace(
            4, "Next action", "decision",
            "Missing city; ask for it.",
        ))
        return _response(
            session_id,
            "Got it — I'll remember those preferences. Which city should I search in?",
            new_state, activity, trace, [], 0, 0, 0, started,
        )
    
    # Form plan
    plan = [f"search {new_state.location}"]
    if new_state.preferred_cuisine:
        plan.append(f"filter {new_state.preferred_cuisine}")
    if new_state.disliked_cuisines:
        plan.append(f"exclude {', '.join(sorted(new_state.disliked_cuisines))}")
    if new_state.diet:
        plan.append(f"enforce {new_state.diet.value}")
    plan.append("rank safe options")
    
    activity.append(_event(
        "plan", "decision", "Plan formed",
        " → ".join(plan).capitalize() + ".",
    ))
    trace.append(_trace(
        4, "Plan", "plan",
        " → ".join(plan),
    ))
    
    # ========== ACT & OBSERVE: Search ==========
    try:
        activity.append(_event(
            "find-call", "tool", "Calling find_restaurants()",
            f"Searching the local index for {new_state.location}.",
        ))
        trace.append(_trace(
            5, "Tool Call", "tool",
            "Searching because a valid city is available.",
            "find_restaurants", {"city": new_state.location},
        ))
        
        search_results = find_restaurants(new_state.location)
        trace[-1]["result"] = f"{len(search_results)} restaurants found"
        
        activity.append(_event(
            "find-result", "observation", "Restaurant search complete",
            f"Found {len(search_results)} restaurants in {new_state.location}.",
        ))
        trace.append(_trace(
            6, "Tool Result", "observation",
            f"find_restaurants returned {len(search_results)} records.",
            result=f"{len(search_results)} restaurants found",
        ))
    
    except Exception as e:
        activity.append(_event(
            "tool-error", "warning", "Search temporarily failed",
            f"The tool reported an error: {str(e)[:80]}",
        ))
        trace.append(_trace(
            6, "Tool Result", "observation",
            "find_restaurants raised an error.",
            "find_restaurants", {"city": new_state.location}, "Tool error",
        ))
        return _response(
            session_id,
            "Restaurant search temporarily failed. Please try again.",
            new_state, activity, trace, [], 0, 0, 0, started,
            memory_override=saved_mem if 'saved_mem' in locals() else get_memory(session_id),
        )
    
    if not search_results:
        activity.append(_event(
            "no-results", "warning", "No restaurants found",
            f"The dataset has no entries for {new_state.location}.",
        ))
        trace.append(_trace(
            7, "Filter Result", "observation",
            f"No restaurants found in {new_state.location}.",
        ))
        return _response(
            session_id,
            f"I couldn't find restaurants in {new_state.location}. "
            f"Try: {', '.join(CITIES[:4])}, or other major cities.",
            new_state, activity, trace, [], 0, 0, 0, started,
            memory_override=saved_mem if 'saved_mem' in locals() else get_memory(session_id),
        )
    
    # ========== ACT & OBSERVE: Cuisine Filter ==========
    cuisine_results = list(search_results)
    cuisine_count = len(search_results)
    
    if new_state.preferred_cuisine:
        activity.append(_event(
            "cuisine-call", "tool", "Calling filter_by_cuisine()",
            f"Narrowing the observation to {new_state.preferred_cuisine}.",
        ))
        trace.append(_trace(
            7, "Tool Call", "tool",
            "Cuisine was explicitly requested, so the previous observation is filtered.",
            "filter_by_cuisine", {"type": new_state.preferred_cuisine},
        ))
        
        try:
            cuisine_results = filter_by_cuisine(new_state.preferred_cuisine)
        except Exception as e:
            activity.append(_event(
                "cuisine-error", "warning", "Cuisine filter failed",
                f"Filter error: {str(e)[:80]}",
            ))
            trace.append(_trace(
                8, "Tool Result", "observation",
                "filter_by_cuisine raised an error.",
                "filter_by_cuisine", {"type": new_state.preferred_cuisine}, "Tool error",
            ))
            return _response(
                session_id,
                "Cuisine filtering temporarily failed. Please try again.",
                new_state, activity, trace, [], len(search_results), 0, 0, started,
                memory_override=saved_mem if 'saved_mem' in locals() else get_memory(session_id),
            )
        
        # Defensive locality check
        city_key = str(new_state.location).casefold()
        cuisine_results = [
            r for r in cuisine_results
            if str(r.get("city", "")).casefold() == city_key
        ]
        
        # If filter_by_cuisine didn't work, fall back to manual filtering
        if not cuisine_results:
            cuisine_results = [
                r for r in search_results
                if _cuisine_matches(r, new_state.preferred_cuisine)
            ]
        
        trace.append(_trace(
            8, "Tool Result", "observation",
            f"filter_by_cuisine returned {len(cuisine_results)} matches.",
            result=f"{len(cuisine_results)} cuisine matches",
        ))
        
        activity.append(_event(
            "cuisine-result", "observation", "Cuisine filter complete",
            f"Found {len(cuisine_results)} {new_state.preferred_cuisine} restaurants in {new_state.location}.",
        ))
    
    # ========== HARD CONSTRAINT: Disliked Cuisines ==========
    if new_state.disliked_cuisines:
        before = len(cuisine_results)
        cuisine_results = [
            r for r in cuisine_results
            if not _is_disliked_cuisine(r, new_state.disliked_cuisines)
        ]
        removed = before - len(cuisine_results)
        
        if removed > 0:
            activity.append(_event(
                "dislike-filter", "decision", "Applying cuisine exclusion",
                f"Removed {removed} option(s) with disliked cuisine(s).",
            ))
            trace.append(_trace(
                9, "Dislike Guardrail", "filter",
                f"Excluded {', '.join(sorted(new_state.disliked_cuisines))}. "
                f"{len(cuisine_results)} remain.",
            ))
    
    # ========== HARD CONSTRAINT: Dietary ==========
    before_diet = len(cuisine_results)
    safe_results = [
        r for r in cuisine_results
        if _diet_compatible(r, new_state.diet)
    ]
    removed_diet = before_diet - len(safe_results)
    
    activity.append(_event(
        "diet-filter", "decision", "Applying dietary guardrail",
        f"Kept {len(safe_results)} safe option(s); removed {removed_diet} incompatible.",
    ))
    trace.append(_trace(
        10, "Dietary Guardrail", "filter",
        f"Applied hard dietary requirement: {new_state.diet.value if new_state.diet else 'none'}. "
        f"{len(safe_results)} remain.",
    ))
    
    # ========== DECIDE: No Safe Match ==========
    if not safe_results:
        constraints = []
        if new_state.preferred_cuisine:
            constraints.append(new_state.preferred_cuisine)
        if new_state.disliked_cuisines:
            constraints.append(f"avoiding {', '.join(sorted(new_state.disliked_cuisines))}")
        if new_state.diet:
            constraints.append(new_state.diet.value)
        
        constraint_desc = " and ".join(constraints) if constraints else "your preferences"
        
        activity.append(_event(
            "no-safe-match", "warning", "No safe matches",
            f"After applying hard constraints, no restaurants remain.",
        ))
        trace.append(_trace(
            11, "Final Recommendation", "result",
            "No safe recommendation exists after hard constraints.",
        ))
        
        # Detailed explanation
        if len(search_results) > 0 and len(safe_results) == 0:
            if removed_diet > 0 and new_state.diet:
                reply = (
                    f"I found {len(search_results)} restaurants in {new_state.location}, "
                    f"including {len(cuisine_results)} matching {constraint_desc}, "
                    f"but none satisfied your {new_state.diet.value} requirement."
                )
            else:
                reply = (
                    f"I found {len(search_results)} restaurants in {new_state.location}, "
                    f"but none matched {constraint_desc}."
                )
        else:
            reply = (
                f"I searched {new_state.location} but couldn't find restaurants "
                f"matching {constraint_desc}. Try relaxing a preference?"
            )
        
        return _response(
            session_id,
            reply,
            new_state, activity, trace, [],
            len(search_results), len(cuisine_results), len(safe_results), started,
            memory_override=saved_mem if 'saved_mem' in locals() else get_memory(session_id),
        )
    
    # ========== DECIDE: Rank Safe Candidates ==========
    ranked = _rank(safe_results, new_state)
    
    activity.append(_event(
        "rank", "decision", "Ranking remaining options",
        f"Scoring {len(ranked)} safe candidate(s) using cuisine, diet, rating, budget, taste, and distance.",
    ))
    activity.append(_event(
        "ready", "success", "Recommendation ready",
        f"Top-ranked option is {ranked[0]['name']} at {ranked[0]['score']}/100.",
    ))
    trace.append(_trace(
        11, "Ranking", "decision",
        "All hard constraints were enforced before scoring.",
    ))
    trace.append(_trace(
        12, "Final Recommendation", "result",
        f"Returned {len(ranked)} ranked safe candidate(s) with transparent score breakdowns.",
    ))
    
    best = ranked[0]
    count_word = "match" if len(ranked) == 1 else "matches"
    
    return _response(
        session_id,
        f"I found {len(ranked)} safe {count_word} in {new_state.location}. "
        f"{best['name']} is the strongest overall fit at {best['score']}/100.",
        new_state, activity, trace, ranked[:5],
        len(search_results), len(cuisine_results), len(safe_results), started,
        memory_override=saved_mem if 'saved_mem' in locals() else get_memory(session_id),
    )
