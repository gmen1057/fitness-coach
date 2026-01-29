"""
Tests for graph provider implementations.
"""
import pytest
from pathlib import Path
import tempfile

from app.providers.graph import NetworkXGraphProvider, GraphNode


@pytest.fixture
async def temp_graph():
    """Create a temporary graph provider for testing."""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        temp_path = f.name

    provider = NetworkXGraphProvider(storage_path=temp_path)
    await provider.initialize()
    yield provider
    await provider.close()

    # Cleanup
    Path(temp_path).unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_graph_initialization(temp_graph):
    """Test that graph initializes with fitness knowledge."""
    # Should have muscle groups
    chest = await temp_graph.get_node("chest")
    assert chest is not None
    assert chest.node_type == "muscle_group"
    assert chest.properties.get("name") == "Chest"

    # Should have exercises
    squat = await temp_graph.get_node("squat")
    assert squat is not None
    assert squat.node_type == "exercise"


@pytest.mark.asyncio
async def test_add_node(temp_graph):
    """Test adding a custom node."""
    node = await temp_graph.add_node(
        "exercise",
        "custom_exercise",
        {"name": "Custom Exercise", "difficulty": 3}
    )

    assert node.node_type == "exercise"
    assert node.node_id == "custom_exercise"
    assert node.properties["name"] == "Custom Exercise"

    # Verify it's retrievable
    retrieved = await temp_graph.get_node("custom_exercise")
    assert retrieved is not None
    assert retrieved.properties["difficulty"] == 3


@pytest.mark.asyncio
async def test_add_edge(temp_graph):
    """Test adding relationships."""
    # Add custom exercise
    await temp_graph.add_node("exercise", "test_exercise", {"name": "Test"})

    # Link to muscle group
    edge = await temp_graph.add_edge(
        "test_exercise",
        "chest",
        "targets",
        {"primary": True}
    )

    assert edge.from_id == "test_exercise"
    assert edge.to_id == "chest"
    assert edge.relationship == "targets"
    assert edge.properties["primary"] is True


@pytest.mark.asyncio
async def test_get_related(temp_graph):
    """Test finding related nodes."""
    # Find exercises targeting chest (incoming edges)
    chest_exercises = await temp_graph.get_related(
        "chest",
        relationship="targets",
        direction="incoming"
    )

    assert len(chest_exercises) > 0
    exercise_names = [e.properties.get("name") for e in chest_exercises]
    assert "Push-up" in exercise_names or "Bench Press" in exercise_names

    # Find muscles targeted by squat (outgoing edges)
    squat_muscles = await temp_graph.get_related(
        "squat",
        relationship="targets",
        direction="outgoing"
    )

    assert len(squat_muscles) > 0
    muscle_ids = [m.node_id for m in squat_muscles]
    assert "quads" in muscle_ids


@pytest.mark.asyncio
async def test_query_pattern(temp_graph):
    """Test pattern-based queries."""
    result = await temp_graph.query("exercise->targets->muscle_group")

    assert len(result.nodes) > 0
    assert len(result.edges) > 0

    # Should find both exercises and muscle groups
    node_types = {n.node_type for n in result.nodes}
    assert "exercise" in node_types
    assert "muscle_group" in node_types

    # All edges should be 'targets' relationships
    relationships = {e.relationship for e in result.edges}
    assert relationships == {"targets"}


@pytest.mark.asyncio
async def test_exercise_progressions(temp_graph):
    """Test finding exercise progressions."""
    # Find what push-up progresses to
    progressions = await temp_graph.get_related(
        "push_up",
        relationship="progresses_to",
        direction="outgoing"
    )

    # Should have at least one progression
    assert len(progressions) > 0
    progression_names = [p.properties.get("name") for p in progressions]
    # Check for expected progressions
    assert any("Diamond" in name or "Archer" in name for name in progression_names if name)


@pytest.mark.asyncio
async def test_delete_node(temp_graph):
    """Test deleting nodes."""
    # Add temporary node
    await temp_graph.add_node("exercise", "temp_exercise", {"name": "Temporary"})
    await temp_graph.add_edge("temp_exercise", "chest", "targets", {})

    # Verify it exists
    node = await temp_graph.get_node("temp_exercise")
    assert node is not None

    # Delete it
    await temp_graph.delete_node("temp_exercise")

    # Verify it's gone
    node = await temp_graph.get_node("temp_exercise")
    assert node is None

    # Edge should also be gone
    related = await temp_graph.get_related("chest", direction="incoming")
    temp_ids = [n.node_id for n in related]
    assert "temp_exercise" not in temp_ids


@pytest.mark.asyncio
async def test_persistence(temp_graph):
    """Test that graph persists to file."""
    # Add custom data
    await temp_graph.add_node("user", "test_user", {"name": "Test User"})
    await temp_graph.close()

    # Reload from same file
    provider2 = NetworkXGraphProvider(storage_path=temp_graph.storage_path)
    await provider2.initialize()

    # Custom data should be there
    user = await provider2.get_node("test_user")
    assert user is not None
    assert user.properties["name"] == "Test User"

    # Pre-populated data should also be there
    squat = await provider2.get_node("squat")
    assert squat is not None

    await provider2.close()


@pytest.mark.asyncio
async def test_workout_tracking(temp_graph):
    """Test tracking user workouts."""
    # Create user
    await temp_graph.add_node("user", "user_123", {"name": "John"})

    # Create session
    await temp_graph.add_node(
        "workout_session",
        "session_001",
        {"date": "2026-01-29", "duration_minutes": 45}
    )

    # Link user to session
    await temp_graph.add_edge("user_123", "session_001", "completed", {})

    # Record exercises
    await temp_graph.add_edge(
        "session_001",
        "squat",
        "performed",
        {"weight": 100, "sets": 3, "reps": 8}
    )

    # Query user's sessions
    sessions = await temp_graph.get_related(
        "user_123",
        relationship="completed",
        direction="outgoing"
    )
    assert len(sessions) == 1
    assert sessions[0].node_id == "session_001"

    # Query exercises in session
    exercises = await temp_graph.get_related(
        "session_001",
        relationship="performed",
        direction="outgoing"
    )
    assert len(exercises) == 1
    assert exercises[0].node_id == "squat"
