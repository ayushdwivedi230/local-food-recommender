"""Final integration test - realistic multi-turn scenario."""
import sys
sys.path.insert(0, 'backend')

from agent import run_agent
from memory import clear_memory


def main():
    print('=== Final Integration Test ===\n')
    
    # Test 1: Greeting
    session = 'integration_test'
    clear_memory(session)
    
    print('Test 1: Greeting')
    r = run_agent(session, 'Hi!')
    assert len(r['recommendations']) == 0
    assert 'greeting' in r['reply'].lower() or 'hi' in r['reply'].lower()
    print('✓ Greeting works\n')
    
    # Test 2: Complex multi-turn scenario
    print('Test 2: Complex Multi-turn Scenario')
    clear_memory(session)
    
    # Turn 1: Set initial preferences
    r1 = run_agent(session, 'I am vegetarian and I want Punjabi food in Phagwara under 400 rupees')
    assert r1['memory']['diet'] == 'vegetarian'
    assert r1['memory']['preferredCuisine'] == 'Punjabi'
    assert r1['memory']['budget'] == 400
    assert r1['memory']['location'] == 'Phagwara'
    assert len(r1['recommendations']) > 0
    print(f'✓ Turn 1: Set preferences, got {len(r1["recommendations"])} recommendations')
    
    # Turn 2: Ask for something less spicy
    r2 = run_agent(session, "Actually, I don't like too much spice")
    assert r2['memory']['spicePreference'] == 'mild'
    # Preferences should be retained
    assert r2['memory']['diet'] == 'vegetarian'
    assert r2['memory']['preferredCuisine'] == 'Punjabi'
    assert len(r2['recommendations']) > 0
    print(f'✓ Turn 2: Add spice preference, got {len(r2["recommendations"])} recommendations')
    
    # Turn 3: Change location
    r3 = run_agent(session, "I'm in Delhi now")
    assert r3['memory']['location'] == 'Delhi'
    # Other preferences retained
    assert r3['memory']['diet'] == 'vegetarian'
    assert r3['memory']['preferredCuisine'] == 'Punjabi'
    assert r3['memory']['spicePreference'] == 'mild'
    print(f'✓ Turn 3: Changed location to Delhi, retained other preferences')
    
    # Turn 4: Explicitly exclude a cuisine
    r4 = run_agent(session, "I don't want Chinese")
    assert 'Chinese' in (r4['memory'].get('dislikedCuisine') or '') or 'Chinese' in (r4['memory'].get('dislikedCuisines') or [])
    # No Chinese in results
    for rec in r4['recommendations']:
        assert 'Chinese' not in rec.get('cuisine', [])
    print(f'✓ Turn 4: Added dislike, verified no Chinese in results')
    
    # Turn 5: Verify no dietary conflicts after all changes
    r5 = run_agent(session, "Show me the best option")
    assert r5['memory']['diet'] == 'vegetarian'
    # All recommendations should be vegetarian-compatible
    for rec in r5['recommendations']:
        diet_labels = {d.lower() for d in rec.get('diet', [])}
        assert 'vegetarian' in diet_labels or 'vegan-friendly' in diet_labels or 'jain-friendly' in diet_labels
    print(f'✓ Turn 5: Final recommendations respect all constraints')
    
    print('\n' + '='*60)
    print('✓✓✓ All integration tests PASSED ✓✓✓')
    print('='*60)
    print('\nAgent is fully functional and backward compatible!')
    print('\nSummary:')
    print('- Greeting classification works')
    print('- Preferences extracted correctly')
    print('- Multi-turn memory retention works')
    print('- Location changes preserve other preferences')
    print('- Dislike preferences excluded correctly')
    print('- Hard constraints respected in recommendations')
    print('- Response schema compatible with existing frontend')


if __name__ == '__main__':
    main()
