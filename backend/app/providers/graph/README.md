# Graph Provider

Knowledge graph provider for tracking fitness relationships and patterns.

## Overview

The graph provider tracks complex relationships between:
- **Exercises** and **muscle groups**
- Exercise **progressions** (easier → harder variations)
- Exercise **alternatives** (different movements, same muscles)
- User **workout history** and performance trends
- **Training patterns** and preferences

## Architecture

### Protocol-Based Design

The `GraphProvider` protocol defines a standard interface, allowing multiple implementations:

- **NetworkX** (default): Lightweight in-memory graph with JSON persistence
- **Neo4j** (optional): Production-grade graph database for scale

### Node Types

| Type | Description | Example Properties |
|------|-------------|-------------------|
| `exercise` | Exercise or movement | `name`, `difficulty`, `equipment` |
| `muscle_group` | Target muscle group | `name` |
| `user` | User profile | `name`, `level` |
| `workout_session` | Completed workout | `date`, `duration_minutes`, `location` |
| `progression` | Exercise progression level | `level`, `requirements` |

### Relationship Types

| Relationship | From → To | Properties | Example |
|--------------|-----------|------------|---------|
| `targets` | Exercise → Muscle | `primary` (bool) | squat → quads (primary=True) |
| `progresses_to` | Exercise → Exercise | `difficulty_increase` | push_up → diamond_push_up |
| `alternative_to` | Exercise → Exercise | `reason` | bench_press → push_up |
| `completed` | User → Session | - | user_123 → session_20260129 |
| `performed` | Session → Exercise | `weight`, `sets`, `reps` | session → squat (100kg, 3x8) |

## Usage

### Basic Setup

```python
from app.providers import get_graph_provider

# Get configured provider (defaults to NetworkX)
graph = await get_graph_provider()

# Use Neo4j instead (requires FITNESS_GRAPH_PROVIDER=neo4j in .env)
graph = await get_graph_provider()
```

### Pre-populated Knowledge

On first initialization, the graph is pre-populated with:
- 15+ common muscle groups
- 16+ basic exercises (push-up, squat, pull-up, etc.)
- Exercise → muscle group relationships
- Exercise progressions (e.g., push-up → diamond push-up)
- Exercise alternatives (e.g., bench press ↔ push-up)

### Adding Nodes

```python
# Add a custom exercise
await graph.add_node(
    "exercise",
    "bulgarian_split_squat",
    {
        "name": "Bulgarian Split Squat",
        "difficulty": 4,
        "equipment": "dumbbell",
    }
)

# Add muscle group relationships
await graph.add_edge("bulgarian_split_squat", "quads", "targets", {"primary": True})
await graph.add_edge("bulgarian_split_squat", "glutes", "targets", {"primary": True})
```

### Tracking Workouts

```python
from datetime import datetime

# Create workout session
session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
await graph.add_node(
    "workout_session",
    session_id,
    {
        "date": datetime.now().isoformat(),
        "duration_minutes": 45,
    }
)

# Link user to session
await graph.add_edge(user_id, session_id, "completed", {})

# Record exercise performance
await graph.add_edge(
    session_id,
    "squat",
    "performed",
    {
        "weight": 100,
        "sets": 3,
        "reps": 8,
        "timestamp": datetime.now().isoformat(),
    }
)
```

### Querying Relationships

```python
# Find all exercises targeting chest
chest_exercises = await graph.get_related(
    "chest",
    relationship="targets",
    direction="incoming",  # Reverse direction
)

# Find squat progressions
progressions = await graph.get_related(
    "squat",
    relationship="progresses_to",
    direction="outgoing",
)

# Find bench press alternatives
alternatives = await graph.get_related(
    "bench_press",
    relationship="alternative_to",
    direction="both",  # Either direction
)
```

### Pattern Queries

```python
# NetworkX: Simple pattern syntax
result = await graph.query("exercise->targets->muscle_group")

# Neo4j: Full Cypher query
result = await graph.query(
    """
    MATCH (e:Exercise)-[r:TARGETS]->(m:MuscleGroup)
    WHERE m.name = $muscle
    RETURN e, r, m
    """,
    params={"muscle": "chest"}
)

# Access results
for node in result.nodes:
    print(f"{node.node_type}: {node.node_id} - {node.properties}")

for edge in result.edges:
    print(f"{edge.from_id} --[{edge.relationship}]-> {edge.to_id}")
```

## Configuration

### Environment Variables

```bash
# Graph provider selection
FITNESS_GRAPH_PROVIDER=networkx  # or "neo4j" or "none"

# NetworkX settings
FITNESS_GRAPH_STORAGE_PATH=./data/fitness_graph.json

# Neo4j settings (optional)
FITNESS_NEO4J_URI=neo4j://localhost:7687
FITNESS_NEO4J_USERNAME=neo4j
FITNESS_NEO4J_PASSWORD=password
```

### Default Settings

In `app/config.py`:

```python
class Settings(BaseSettings):
    graph_provider: Literal["networkx", "neo4j", "none"] = "networkx"
    graph_storage_path: str = "./data/fitness_graph.json"
    neo4j_uri: str | None = None
    neo4j_username: str = "neo4j"
    neo4j_password: SecretStr | None = None
```

## Implementation Details

### NetworkX Provider

**Pros:**
- Zero external dependencies (besides NetworkX)
- Simple JSON file persistence
- Perfect for single-user deployments
- Fast in-memory queries

**Cons:**
- Limited query language (simple patterns only)
- Single process only (no horizontal scaling)
- No built-in graph algorithms

**Storage format:**
```json
{
  "nodes": [
    {"id": "squat", "type": "exercise", "properties": {"name": "Squat"}}
  ],
  "edges": [
    {"from_id": "squat", "to_id": "quads", "relationship": "targets", "properties": {"primary": true}}
  ]
}
```

### Neo4j Provider

**Pros:**
- Production-grade graph database
- Full Cypher query language
- Graph algorithms (PageRank, community detection, etc.)
- Horizontal scaling support

**Cons:**
- Requires Neo4j server
- Additional infrastructure complexity
- More resource intensive

**Installation:**
```bash
pip install fitness-coach[neo4j]
docker run -d -p 7687:7687 -p 7474:7474 neo4j:5
```

## Examples

See `/opt/helper/opensource/fitness-coach/backend/examples/graph_usage.py` for a comprehensive example demonstrating:
- Querying pre-populated knowledge
- Finding exercise progressions
- Tracking workout history
- Pattern analysis
- Adding custom exercises

Run with:
```bash
cd /opt/helper/opensource/fitness-coach/backend
python -m examples.graph_usage
```

## Use Cases

### 1. Exercise Recommendations

Find alternative exercises targeting the same muscles:
```python
# User can't do pull-ups
pull_up_muscles = await graph.get_related("pull_up", "targets")
alternatives = []
for muscle in pull_up_muscles:
    exercises = await graph.get_related(muscle.node_id, "targets", direction="incoming")
    alternatives.extend(exercises)
```

### 2. Progressive Overload Tracking

Track weight progression over time:
```python
# Find all sessions where user performed squats
user_sessions = await graph.get_related(user_id, "completed")
squat_history = []
for session in user_sessions:
    # Check if squat was performed
    exercises = await graph.get_related(session.node_id, "performed")
    for ex in exercises:
        if ex.node_id == "squat":
            # Get performance data from edge properties
            edge = ... # Query the edge for weight/reps
            squat_history.append(edge.properties)
```

### 3. Training Volume Analysis

Calculate total volume per muscle group:
```python
# Get all exercises from recent sessions
volume_by_muscle = {}
for session in recent_sessions:
    exercises = await graph.get_related(session.node_id, "performed")
    for ex in exercises:
        muscles = await graph.get_related(ex.node_id, "targets")
        for muscle in muscles:
            # Add sets x reps to muscle volume
            volume_by_muscle[muscle.node_id] = ...
```

## Future Enhancements

- Graph neural networks for exercise similarity
- Community detection for muscle group clustering
- Centrality analysis to identify key exercises
- Temporal graph analysis for training periodization
- Integration with RAG provider for semantic search
