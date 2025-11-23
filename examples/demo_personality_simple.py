"""
Demo script for simplified personality system.

Tests emotion detection, intent classification, and personality adaptation
without any async/agent complexity.
"""

from freya.personality import PersonalityEngine


def demo_personality():
    """Run personality system demo with various scenarios."""
    print("=" * 70)
    print("FREYA PERSONALITY SYSTEM DEMO (Simplified)")
    print("=" * 70)
    print()

    # Create personality engine
    config = {
        "traits": {
            "directness": 0.8,
            "humor_level": 0.7,
            "empathy": 0.7,
            "formality": 0.2,
            "verbosity": 0.6,
            "curiosity": 0.7,
            "sassiness": 0.6,
            "patience": 0.8,
        }
    }

    engine = PersonalityEngine(config)
    print("Personality engine initialized with base traits")
    print()

    # Test scenarios
    scenarios = [
        {
            "name": "Sad User - Failed Exam",
            "query": "I just failed my exam and I'm devastated",
        },
        {
            "name": "Happy User - Got the Job",
            "query": "OMG I got the job! This is amazing!!!",
        },
        {
            "name": "Frustrated User - Technical Issue",
            "query": "Ugh, this code keeps breaking and it's so annoying!",
        },
        {
            "name": "Confused User - Needs Help",
            "query": "I don't understand how Python classes work at all",
        },
        {
            "name": "Curious User - Learning",
            "query": "Can you help me understand how quantum computing works?",
        },
        {
            "name": "Philosophical - Deep Question",
            "query": "What's the meaning of life, you think?",
        },
        {
            "name": "Urgent Request",
            "query": "URGENT! I need help with this right now!!!",
        },
        {
            "name": "Playful - Joking Around",
            "query": "haha that's hilarious! tell me another joke",
        },
    ]

    for i, scenario in enumerate(scenarios, 1):
        print(f"\n{'-' * 70}")
        print(f"Scenario {i}: {scenario['name']}")
        print(f"Query: \"{scenario['query']}\"")
        print()

        # Analyze and get personality instructions
        instructions = engine.analyze_and_adapt(scenario["query"])

        # Get current state
        state = engine.get_state_summary()

        print("Freya's State:")
        print(f"  Emotional State: {state['emotional_state']}")
        print(f"  Mode: {state['mode']}")
        print(f"  Energy Level: {state['energy_level']}")
        print(f"  Conversation Depth: {state['conversation_depth']}")
        print()

        if instructions:
            print("Personality Instructions for LLM:")
            print(instructions)
        else:
            print("  (No specific personality instructions)")

        print()

    # Final mood summary
    print(f"\n{'=' * 70}")
    print("FINAL MOOD SUMMARY")
    print(f"{'=' * 70}")
    state = engine.get_state_summary()
    print(f"After {state['conversation_count']} interactions:")
    print(f"  Emotional State: {state['emotional_state']}")
    print(f"  Mode: {state['mode']}")
    print(f"  Energy Level: {state['energy_level']}")
    print(f"  Conversation Depth: {state['conversation_depth']}")


if __name__ == "__main__":
    demo_personality()
