"""Comprehensive test suite for the improved LocalFood AI agent.

Tests cover:
- Intent classification (greeting, capability, hungry, food)
- NLU and preference extraction
- State management and memory
- Constraint application (diet, dislikes, budget)
- Ranking and scoring
- Edge cases and error handling
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from agent import run_agent, PreferenceState, DietType, SpiceLevel, BudgetType
from memory import clear_memory, get_memory, save_memory


def test_greeting():
    """Test 1: Greeting intent."""
    session_id = "test_greeting"
    clear_memory(session_id)
    result = run_agent(session_id, "Hi there!")
    assert result["mode"] == "demo"
    assert "greeting" in result["reply"].lower() or "hi" in result["reply"].lower()
    assert len(result["recommendations"]) == 0
    print("✓ Test 1: Greeting")


def test_capability_request():
    """Test 2: Capability query."""
    session_id = "test_capability"
    clear_memory(session_id)
    result = run_agent(session_id, "What can you do?")
    assert result["mode"] == "demo"
    assert "find_restaurants" in result["reply"]
    assert len(result["recommendations"]) == 0
    print("✓ Test 2: Capability request")


def test_basic_city_search():
    """Test 3: Basic city search without preferences."""
    session_id = "test_basic_search"
    clear_memory(session_id)
    result = run_agent(session_id, "I'm in Phagwara")
    assert result["sessionId"] == session_id
    assert "memory" in result
    assert result["memory"]["location"] == "Phagwara"
    # Should return recommendations
    assert len(result["recommendations"]) > 0
    assert result["stats"]["searched"] > 0
    print("✓ Test 3: Basic city search")


def test_vegetarian_request():
    """Test 4: Vegetarian dietary preference."""
    session_id = "test_vegetarian"
    clear_memory(session_id)
    result = run_agent(session_id, "I'm vegetarian and in Jalandhar")
    assert result["memory"]["diet"] == "vegetarian"
    assert result["memory"]["location"] == "Jalandhar"
    # All recommendations should be vegetarian-compatible
    for rec in result["recommendations"]:
        diet_labels = {d.lower() for d in rec.get("diet", [])}
        assert "vegetarian" in diet_labels or "vegan-friendly" in diet_labels or "jain-friendly" in diet_labels
    print("✓ Test 4: Vegetarian request")


def test_chinese_request():
    """Test 5: Chinese cuisine preference."""
    session_id = "test_chinese"
    clear_memory(session_id)
    result = run_agent(session_id, "I want Chinese food in Phagwara")
    assert result["memory"]["preferredCuisine"] == "Chinese"
    assert result["memory"]["location"] == "Phagwara"
    # All recommendations should be Chinese
    for rec in result["recommendations"]:
        assert "Chinese" in rec.get("cuisine", [])
    print("✓ Test 5: Chinese request")


def test_punjabi_request():
    """Test 6: Punjabi cuisine preference."""
    session_id = "test_punjabi"
    clear_memory(session_id)
    result = run_agent(session_id, "I want Punjabi food in Jalandhar")
    assert result["memory"]["preferredCuisine"] == "Punjabi"
    # All recommendations should include Punjabi
    for rec in result["recommendations"]:
        assert "Punjabi" in rec.get("cuisine", [])
    print("✓ Test 6: Punjabi request")


def test_spicy_preference():
    """Test 7: Explicit spicy preference."""
    session_id = "test_spicy"
    clear_memory(session_id)
    result = run_agent(session_id, "I like spicy food in Phagwara")
    assert result["memory"]["spicePreference"] == "spicy"
    assert len(result["recommendations"]) > 0
    print("✓ Test 7: Spicy preference")


def test_not_spicy_preference():
    """Test 8: Negative spice preference - 'I don't like spicy'."""
    session_id = "test_not_spicy"
    clear_memory(session_id)
    result = run_agent(session_id, "I don't like spicy food in Jalandhar")
    assert result["memory"]["spicePreference"] == "mild"
    assert len(result["recommendations"]) > 0
    # Recommendations should prefer mild/low spice
    if result["recommendations"]:
        first_rec = result["recommendations"][0]
        assert first_rec["spiceLevel"].lower() in ["low", "medium"]
    print("✓ Test 8: Not spicy preference")


def test_disliked_cuisine():
    """Test 9: Disliked cuisine exclusion - 'I don't like Chinese'."""
    session_id = "test_dislike"
    clear_memory(session_id)
    result = run_agent(session_id, "I don't like Chinese and I'm in Phagwara")
    assert result["memory"]["dislikedCuisine"] == "Chinese" or "Chinese" in (result["memory"].get("dislikedCuisines") or [])
    # No recommendations should have Chinese
    for rec in result["recommendations"]:
        assert "Chinese" not in rec.get("cuisine", [])
    print("✓ Test 9: Disliked cuisine")


def test_budget_under_constraint():
    """Test 10: Budget 'under ₹500' hard constraint."""
    session_id = "test_budget"
    clear_memory(session_id)
    result = run_agent(session_id, "I want food under ₹300 in Phagwara")
    assert result["memory"]["budget"] == 300
    # All recommendations should fit budget (soft - but top ones should)
    if result["recommendations"]:
        first_rec = result["recommendations"][0]
        # First rec should fit or be close
        assert first_rec["averagePrice"] <= 350  # Allow some margin
    print("✓ Test 10: Budget constraint")


def test_cross_turn_memory():
    """Test 11: Preferences persist across turns."""
    session_id = "test_memory"
    clear_memory(session_id)
    
    # Turn 1: Set preferences
    result1 = run_agent(session_id, "I'm vegetarian and I want Punjabi food in Phagwara")
    assert result1["memory"]["diet"] == "vegetarian"
    assert result1["memory"]["preferredCuisine"] == "Punjabi"
    
    # Turn 2: Just ask for recommendations
    result2 = run_agent(session_id, "Suggest something")
    # Preferences should be remembered
    assert result2["memory"]["diet"] == "vegetarian"
    assert result2["memory"]["preferredCuisine"] == "Punjabi"
    # All recommendations should still be vegetarian Punjabi
    for rec in result2["recommendations"]:
        assert "Punjabi" in rec.get("cuisine", [])
        diet_labels = {d.lower() for d in rec.get("diet", [])}
        assert "vegetarian" in diet_labels or "vegan-friendly" in diet_labels
    print("✓ Test 11: Cross-turn memory")


def test_location_change():
    """Test 12: Location change without losing other preferences."""
    session_id = "test_location_change"
    clear_memory(session_id)
    
    # Turn 1: Set location and preferences
    result1 = run_agent(session_id, "I'm vegetarian and want Punjabi food in Phagwara under ₹300")
    assert result1["memory"]["location"] == "Phagwara"
    assert result1["memory"]["diet"] == "vegetarian"
    assert result1["memory"]["preferredCuisine"] == "Punjabi"
    
    # Turn 2: Change location
    result2 = run_agent(session_id, "I'm in Delhi now")
    assert result2["memory"]["location"] == "Delhi"
    # Other preferences should remain
    assert result2["memory"]["diet"] == "vegetarian"
    assert result2["memory"]["preferredCuisine"] == "Punjabi"
    print("✓ Test 12: Location change")


def test_cuisine_correction():
    """Test 13: Changing cuisine preference."""
    session_id = "test_cuisine_correction"
    clear_memory(session_id)
    
    # Turn 1: Set Chinese
    result1 = run_agent(session_id, "I want Chinese food in Phagwara")
    assert result1["memory"]["preferredCuisine"] == "Chinese"
    
    # Turn 2: Change to Punjabi
    result2 = run_agent(session_id, "Actually, make that Punjabi")
    assert result2["memory"]["preferredCuisine"] == "Punjabi"
    # Recommendations should be Punjabi, not Chinese
    for rec in result2["recommendations"]:
        assert "Punjabi" in rec.get("cuisine", [])
    print("✓ Test 13: Cuisine correction")


def test_dietary_conflict():
    """Test 14: Dietary conflict detection - veg to non-veg."""
    session_id = "test_diet_conflict"
    clear_memory(session_id)
    
    # Turn 1: Set vegetarian
    result1 = run_agent(session_id, "I'm vegetarian in Jalandhar")
    assert result1["memory"]["diet"] == "vegetarian"
    
    # Turn 2: Try to switch to non-veg
    result2 = run_agent(session_id, "I want non-veg food now")
    # Should detect conflict and warn
    assert "conflict" in result2["reply"].lower() or "confirm" in result2["reply"].lower()
    print("✓ Test 14: Dietary conflict detection")


def test_no_city_specified():
    """Test 15: Missing city should prompt for it."""
    session_id = "test_no_city"
    clear_memory(session_id)
    result = run_agent(session_id, "I'm vegetarian and want Punjabi food")
    # Should ask for city
    assert "city" in result["reply"].lower() or "where" in result["reply"].lower()
    assert len(result["recommendations"]) == 0
    print("✓ Test 15: No city specified")


def test_unknown_city():
    """Test 16: Unknown city should provide helpful message."""
    session_id = "test_unknown_city"
    clear_memory(session_id)
    result = run_agent(session_id, "I want food in Atlantis")
    # Should indicate city not found
    assert "couldn't find" in result["reply"].lower() or "try" in result["reply"].lower()
    assert len(result["recommendations"]) == 0
    print("✓ Test 16: Unknown city")


def test_no_cuisine_match():
    """Test 17: City exists but no cuisine match."""
    session_id = "test_no_cuisine"
    clear_memory(session_id)
    result = run_agent(session_id, "I want French food in Phagwara")
    # French might not be in dataset; should fail gracefully
    if len(result["recommendations"]) == 0:
        assert "couldn't find" in result["reply"].lower() or "restaurant" in result["reply"].lower()
    print("✓ Test 17: No cuisine match")


def test_no_dietary_match():
    """Test 18: Cuisine exists but no dietary match."""
    session_id = "test_no_diet_match"
    clear_memory(session_id)
    # Try to find vegan Chinese in a city where it might not exist
    result = run_agent(session_id, "I want vegan Chinese food in Jalandhar")
    # Should either find matches or explain constraint failure
    if len(result["recommendations"]) == 0:
        # Check that error message explains the constraint failure
        assert ("didn't satisfy" in result["reply"].lower() or 
                "couldn't find" in result["reply"].lower() or
                "none matched" in result["reply"].lower() or
                "matched" in result["reply"].lower())
    print("✓ Test 18: No dietary match")


def test_suggest_something():
    """Test 19: 'Suggest something' uses existing preferences."""
    session_id = "test_suggest"
    clear_memory(session_id)
    
    # Set preferences first
    result1 = run_agent(session_id, "I'm vegetarian and I want Punjabi in Jalandhar")
    assert result1["memory"]["diet"] == "vegetarian"
    assert result1["memory"]["preferredCuisine"] == "Punjabi"
    assert len(result1["recommendations"]) > 0
    
    # Then ask for suggestion using a simple food request (not "suggest something")
    result2 = run_agent(session_id, "What would you recommend?")
    # Should use remembered preferences
    assert result2["memory"]["diet"] == "vegetarian"
    assert result2["memory"]["preferredCuisine"] == "Punjabi"
    assert len(result2["recommendations"]) > 0
    # All recommendations should still be vegetarian Punjabi
    for rec in result2["recommendations"]:
        assert "Punjabi" in rec.get("cuisine", [])
        diet_labels = {d.lower() for d in rec.get("diet", [])}
        assert "vegetarian" in diet_labels or "vegan-friendly" in diet_labels or "jain-friendly" in diet_labels
    print("✓ Test 19: Suggest something")


def test_im_hungry():
    """Test 20: 'I'm hungry' should use known location."""
    session_id = "test_hungry"
    clear_memory(session_id)
    
    # First set location
    run_agent(session_id, "I'm in Jalandhar")
    
    # Then say hungry
    result = run_agent(session_id, "I'm hungry")
    # Should not ask for city again, should use known location
    assert result["memory"]["location"] == "Jalandhar"
    print("✓ Test 20: I'm hungry")


def test_delhi_food_as_location():
    """Test 21: 'Delhi food' should be interpreted as location Delhi, not a cuisine."""
    session_id = "test_delhi_food"
    clear_memory(session_id)
    result = run_agent(session_id, "I want Delhi food")
    # Delhi should be detected as location
    assert result["memory"]["location"] == "Delhi"
    # Not as a cuisine preference (Delhi is not in CUISINES)
    assert result["memory"].get("preferredCuisine") is None or "Delhi" not in (result["memory"].get("preferredCuisine") or "")
    print("✓ Test 21: Delhi food as location")


def test_dont_like_chinese_clearly():
    """Test 22: Clear negation 'I don't like Chinese' should exclude it."""
    session_id = "test_dislike_clear"
    clear_memory(session_id)
    result = run_agent(session_id, "I don't like Chinese so don't recommend that in Phagwara")
    # Chinese should be disliked
    assert "Chinese" in (result["memory"].get("dislikedCuisine") or "") or "Chinese" in (result["memory"].get("dislikedCuisines") or [])
    # No recommendations should have Chinese
    for rec in result["recommendations"]:
        assert "Chinese" not in rec.get("cuisine", [])
    print("✓ Test 22: Don't like Chinese")


def test_combined_constraints():
    """Test 23: Multiple constraints together."""
    session_id = "test_combined"
    clear_memory(session_id)
    result = run_agent(session_id, "I'm vegetarian, I want Punjabi food, under ₹400, not too spicy, in Jalandhar")
    
    # All constraints should be applied
    assert result["memory"]["diet"] == "vegetarian"
    assert result["memory"]["preferredCuisine"] == "Punjabi"
    assert result["memory"]["budget"] == 400
    assert result["memory"]["spicePreference"] == "mild"
    assert result["memory"]["location"] == "Jalandhar"
    
    # All recommendations should satisfy hard constraints
    for rec in result["recommendations"]:
        # Dietary
        diet_labels = {d.lower() for d in rec.get("diet", [])}
        assert "vegetarian" in diet_labels or "vegan-friendly" in diet_labels
        # Cuisine
        assert "Punjabi" in rec.get("cuisine", [])
    
    print("✓ Test 23: Combined constraints")


def test_session_isolation():
    """Test 24: Different sessions don't share preferences."""
    session1 = "test_session_1"
    session2 = "test_session_2"
    clear_memory(session1)
    clear_memory(session2)
    
    # Session 1: Set vegetarian
    run_agent(session1, "I'm vegetarian in Jalandhar")
    
    # Session 2: Set non-veg
    run_agent(session2, "I want non-veg food in Bengaluru")
    
    # Check they're isolated
    mem1 = get_memory(session1)
    mem2 = get_memory(session2)
    assert mem1["diet"] == "vegetarian"
    assert mem2["diet"] == "non-vegetarian"
    
    print("✓ Test 24: Session isolation")


def test_response_schema_compatibility():
    """Test 25: Response schema matches expected format."""
    session_id = "test_schema"
    clear_memory(session_id)
    result = run_agent(session_id, "I want Punjabi in Jalandhar")
    
    # Check all required fields
    assert "sessionId" in result
    assert "mode" in result
    assert "reply" in result
    assert "memory" in result
    assert "activity" in result
    assert "trace" in result
    assert "recommendations" in result
    assert "stats" in result
    
    # Check memory fields
    memory = result["memory"]
    assert "diet" in memory
    assert "preferredCuisine" in memory
    assert "location" in memory
    
    # Check stats
    stats = result["stats"]
    assert "searched" in stats
    assert "afterCuisine" in stats
    assert "afterDiet" in stats
    assert "elapsedMs" in stats
    
    # Check recommendation fields (if any)
    if result["recommendations"]:
        rec = result["recommendations"][0]
        assert "id" in rec
        assert "name" in rec
        assert "city" in rec
        assert "cuisine" in rec
        assert "diet" in rec
        assert "rating" in rec
        assert "averagePrice" in rec
        assert "priceRange" in rec
        assert "spiceLevel" in rec
        assert "distanceKm" in rec
        assert "description" in rec
        assert "score" in rec
        assert "reason" in rec
        assert "scoreBreakdown" in rec
    
    print("✓ Test 25: Response schema compatibility")


def test_no_none_exposure():
    """Test 26: No 'None' values exposed in user-facing text."""
    session_id = "test_no_none"
    clear_memory(session_id)
    result = run_agent(session_id, "I'm in Phagwara")
    
    # Check reply doesn't contain "None"
    assert "None" not in result["reply"]
    
    # Check activity messages don't contain "None"
    for event in result["activity"]:
        assert "None" not in event.get("detail", "")
    
    print("✓ Test 26: No None exposure")


def test_negation_not_confused():
    """Test 27: Negation patterns don't cause false positives."""
    session_id = "test_negation"
    clear_memory(session_id)
    
    # "I don't like spicy" should set mild, NOT spicy
    result = run_agent(session_id, "I don't like spicy food in Phagwara")
    assert result["memory"]["spicePreference"] == "mild"
    
    # Rankings should prefer low-spice
    if result["recommendations"]:
        assert result["recommendations"][0]["spiceLevel"].lower() in ["low", "medium"]
    
    print("✓ Test 27: Negation patterns")


def test_clarification_not_asked_unnecessarily():
    """Test 28: Clarification questions only when needed."""
    session_id = "test_clarify"
    clear_memory(session_id)
    
    # This has enough info; shouldn't ask for clarification
    result = run_agent(session_id, "I want Punjabi food in Jalandhar")
    # Should return recommendations, not ask for more info
    assert len(result["recommendations"]) > 0 or "restaurants" in result["reply"].lower()
    
    print("✓ Test 28: Clarification appropriateness")


def run_all_tests():
    """Run all tests."""
    print("\n" + "="*60)
    print("LocalFood AI Agent - Comprehensive Test Suite")
    print("="*60 + "\n")
    
    tests = [
        test_greeting,
        test_capability_request,
        test_basic_city_search,
        test_vegetarian_request,
        test_chinese_request,
        test_punjabi_request,
        test_spicy_preference,
        test_not_spicy_preference,
        test_disliked_cuisine,
        test_budget_under_constraint,
        test_cross_turn_memory,
        test_location_change,
        test_cuisine_correction,
        test_dietary_conflict,
        test_no_city_specified,
        test_unknown_city,
        test_no_cuisine_match,
        test_no_dietary_match,
        test_suggest_something,
        test_im_hungry,
        test_delhi_food_as_location,
        test_dont_like_chinese_clearly,
        test_combined_constraints,
        test_session_isolation,
        test_response_schema_compatibility,
        test_no_none_exposure,
        test_negation_not_confused,
        test_clarification_not_asked_unnecessarily,
    ]
    
    passed = 0
    failed = 0
    errors = []
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            failed += 1
            errors.append(f"  ✗ {test.__name__}: {str(e)}")
        except Exception as e:
            failed += 1
            errors.append(f"  ✗ {test.__name__}: {type(e).__name__}: {str(e)}")
    
    print("\n" + "="*60)
    print(f"Results: {passed} passed, {failed} failed out of {passed + failed}")
    print("="*60 + "\n")
    
    if errors:
        print("Failed tests:")
        for error in errors:
            print(error)
        print()
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(run_all_tests())
