"""
Example usage of the Graph Provider for fitness knowledge tracking.

Demonstrates:
- Adding exercises and muscle groups
- Creating relationships (targets, progressions, alternatives)
- Querying the knowledge graph
- Finding related exercises
- Tracking user workout history
"""
import asyncio
from datetime import datetime

from app.providers.graph import get_graph_provider


async def main():
    """Demonstrate graph provider capabilities."""
    # Get the configured graph provider (defaults to NetworkX)
    graph = await get_graph_provider()
    print(f"Using graph provider: {graph.__class__.__name__}\n")

    # === 1. Query pre-populated fitness knowledge ===
    print("=== Pre-populated Exercise Knowledge ===")

    # Find all exercises that target chest
    chest_exercises = await graph.get_related(
        "chest",
        relationship="targets",
        direction="incoming",  # exercises that target chest
    )
    print(f"Exercises targeting chest: {[e.properties.get('name') for e in chest_exercises]}")

    # Find muscle groups targeted by squats
    squat_muscles = await graph.get_related(
        "squat",
        relationship="targets",
        direction="outgoing",
    )
    print(f"Squat targets: {[m.node_id for m in squat_muscles]}\n")

    # === 2. Find exercise progressions ===
    print("=== Exercise Progressions ===")

    # Find what push-up progresses to
    push_up_progressions = await graph.get_related(
        "push_up",
        relationship="progresses_to",
        direction="outgoing",
    )
    print(f"Push-up progressions: {[e.properties.get('name') for e in push_up_progressions]}")

    # Find alternatives to bench press
    bench_alternatives = await graph.get_related(
        "bench_press",
        relationship="alternative_to",
        direction="outgoing",
    )
    print(f"Bench press alternatives: {[e.properties.get('name') for e in bench_alternatives]}\n")

    # === 3. Add custom user data ===
    print("=== Tracking User Workout History ===")

    # Add user node
    user_id = "user_123"
    await graph.add_node("user", user_id, {"name": "John Doe"})

    # Record a workout session
    session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    await graph.add_node(
        "workout_session",
        session_id,
        {
            "date": datetime.now().isoformat(),
            "duration_minutes": 45,
            "location": "gym",
        },
    )

    # Link user to session
    await graph.add_edge(user_id, session_id, "completed", {})

    # Record exercises performed in this session
    exercises_performed = [
        ("squat", {"weight": 100, "sets": 3, "reps": 8}),
        ("bench_press", {"weight": 80, "sets": 3, "reps": 10}),
        ("pull_up", {"weight": 0, "sets": 3, "reps": 12}),
    ]

    for exercise_id, performance in exercises_performed:
        await graph.add_edge(
            session_id,
            exercise_id,
            "performed",
            {
                **performance,
                "timestamp": datetime.now().isoformat(),
            },
        )

    print(f"Recorded workout session: {session_id}")
    print(f"Exercises: {[e[0] for e in exercises_performed]}\n")

    # === 4. Query user's workout history ===
    print("=== User's Recent Workouts ===")

    # Find all sessions for this user
    user_sessions = await graph.get_related(
        user_id,
        relationship="completed",
        direction="outgoing",
    )
    print(f"Total sessions: {len(user_sessions)}")

    for session in user_sessions:
        session_date = session.properties.get("date", "unknown")
        print(f"  Session: {session.node_id} ({session_date})")

        # Find exercises in this session
        exercises = await graph.get_related(
            session.node_id,
            relationship="performed",
            direction="outgoing",
        )
        for exercise in exercises:
            print(f"    - {exercise.properties.get('name', exercise.node_id)}")

    print()

    # === 5. Advanced query: Exercise patterns ===
    print("=== Exercise Pattern Analysis ===")

    # Query all exercise -> muscle_group relationships
    result = await graph.query("exercise->targets->muscle_group")
    print(f"Total exercise-muscle relationships: {len(result.edges)}")

    # Group by muscle group to see coverage
    muscle_coverage = {}
    for edge in result.edges:
        muscle = edge.to_id
        if muscle not in muscle_coverage:
            muscle_coverage[muscle] = []
        exercise_node = next((n for n in result.nodes if n.node_id == edge.from_id), None)
        if exercise_node:
            muscle_coverage[muscle].append(exercise_node.properties.get("name", edge.from_id))

    print("Muscle group coverage:")
    for muscle, exercises in sorted(muscle_coverage.items()):
        print(f"  {muscle.title()}: {len(exercises)} exercises")

    print()

    # === 6. Add custom exercise ===
    print("=== Adding Custom Exercise ===")

    # Add a custom variation
    await graph.add_node(
        "exercise",
        "bulgarian_split_squat",
        {
            "name": "Bulgarian Split Squat",
            "difficulty": 4,
            "equipment": "dumbbell",
        },
    )

    # Link to muscle groups
    await graph.add_edge("bulgarian_split_squat", "quads", "targets", {"primary": True})
    await graph.add_edge("bulgarian_split_squat", "glutes", "targets", {"primary": True})
    await graph.add_edge("bulgarian_split_squat", "hamstrings", "targets", {"primary": False})

    # Mark as progression from regular squat
    await graph.add_edge(
        "squat",
        "bulgarian_split_squat",
        "progresses_to",
        {"difficulty_increase": 2, "unilateral": True},
    )

    print("Added Bulgarian Split Squat to knowledge graph")
    print("  Targets: quads (primary), glutes (primary), hamstrings (secondary)")
    print("  Progression from: squat\n")

    # Verify it's findable
    squat_progressions = await graph.get_related("squat", "progresses_to")
    print(f"All squat progressions: {[e.properties.get('name', e.node_id) for e in squat_progressions]}")

    # === Cleanup ===
    await graph.close()
    print("\nGraph provider closed successfully")


if __name__ == "__main__":
    asyncio.run(main())
