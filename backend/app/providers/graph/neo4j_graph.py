"""
Neo4j-based knowledge graph provider (optional).

Requires Neo4j database and neo4j Python driver.
Install with: pip install "fitness-coach[neo4j]"
"""
from typing import Any

try:
    from neo4j import AsyncGraphDatabase, AsyncDriver
    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False
    AsyncDriver = Any  # Type stub

from .protocols import GraphNode, GraphEdge, GraphQueryResult


class Neo4jGraphProvider:
    """
    Production-grade knowledge graph using Neo4j.

    Supports complex Cypher queries, relationship patterns, and graph algorithms.
    """

    def __init__(
        self,
        uri: str = "neo4j://localhost:7687",
        username: str = "neo4j",
        password: str = "password",
    ):
        """
        Initialize Neo4j graph provider.

        Args:
            uri: Neo4j connection URI
            username: Database username
            password: Database password

        Raises:
            ImportError: If neo4j package is not installed
        """
        if not NEO4J_AVAILABLE:
            raise ImportError(
                "Neo4j provider requires the neo4j package. "
                "Install with: pip install 'fitness-coach[neo4j]'"
            )

        self.uri = uri
        self.username = username
        self.password = password
        self.driver: AsyncDriver | None = None
        self._initialized = False

    async def initialize(self) -> None:
        """Connect to Neo4j and create indexes."""
        if self._initialized:
            return

        self.driver = AsyncGraphDatabase.driver(
            self.uri,
            auth=(self.username, self.password),
        )

        # Create indexes for performance
        async with self.driver.session() as session:
            await session.run(
                "CREATE INDEX node_id_index IF NOT EXISTS FOR (n:Node) ON (n.id)"
            )
            await session.run(
                "CREATE INDEX exercise_name_index IF NOT EXISTS FOR (n:Exercise) ON (n.name)"
            )
            await session.run(
                "CREATE INDEX muscle_group_index IF NOT EXISTS FOR (n:MuscleGroup) ON (n.name)"
            )

        # Initialize with fitness knowledge
        await self._initialize_fitness_knowledge()

        self._initialized = True

    async def _initialize_fitness_knowledge(self) -> None:
        """Pre-populate with exercise knowledge (same as NetworkX version)."""
        # Check if already populated
        async with self.driver.session() as session:
            result = await session.run("MATCH (n) RETURN count(n) as count")
            record = await result.single()
            if record and record["count"] > 0:
                return  # Already initialized

        # Muscle groups
        muscle_groups = [
            "chest", "back", "shoulders", "biceps", "triceps",
            "forearms", "abs", "obliques", "quads", "hamstrings",
            "glutes", "calves", "traps", "lats", "delts",
        ]
        for mg in muscle_groups:
            await self.add_node("muscle_group", mg, {"name": mg.title()})

        # Common exercises
        exercises = [
            ("push_up", "Push-up", ["chest", "triceps", "shoulders"]),
            ("bench_press", "Bench Press", ["chest", "triceps", "shoulders"]),
            ("pull_up", "Pull-up", ["lats", "back", "biceps"]),
            ("squat", "Squat", ["quads", "glutes", "hamstrings"]),
            ("deadlift", "Deadlift", ["back", "hamstrings", "glutes", "traps"]),
            ("overhead_press", "Overhead Press", ["delts", "shoulders", "triceps"]),
            ("plank", "Plank", ["abs", "obliques"]),
        ]

        for exercise_id, exercise_name, targets in exercises:
            await self.add_node("exercise", exercise_id, {"name": exercise_name})
            for muscle in targets:
                await self.add_edge(
                    exercise_id,
                    muscle,
                    "targets",
                    {"primary": muscle in targets[:1]},
                )

    async def add_node(
        self,
        node_type: str,
        node_id: str,
        properties: dict | None = None,
    ) -> GraphNode:
        """Add or update a node in Neo4j."""
        props = properties or {}
        props["id"] = node_id
        props["type"] = node_type

        # Create Cypher query with proper escaping
        prop_str = ", ".join(f"n.{k} = ${k}" for k in props.keys())

        query = f"""
        MERGE (n {{id: $id}})
        SET {prop_str}
        RETURN n
        """

        async with self.driver.session() as session:
            await session.run(query, **props)

        return GraphNode(node_type=node_type, node_id=node_id, properties=properties or {})

    async def add_edge(
        self,
        from_id: str,
        to_id: str,
        relationship: str,
        properties: dict | None = None,
    ) -> GraphEdge:
        """Add or update an edge in Neo4j."""
        props = properties or {}

        # Use MERGE to avoid duplicates
        query = """
        MATCH (a {id: $from_id})
        MATCH (b {id: $to_id})
        MERGE (a)-[r:RELATES {type: $relationship}]->(b)
        SET r += $properties
        RETURN r
        """

        async with self.driver.session() as session:
            await session.run(
                query,
                from_id=from_id,
                to_id=to_id,
                relationship=relationship,
                properties=props,
            )

        return GraphEdge(
            from_id=from_id,
            to_id=to_id,
            relationship=relationship,
            properties=props,
        )

    async def get_node(self, node_id: str) -> GraphNode | None:
        """Get a node by ID."""
        query = "MATCH (n {id: $node_id}) RETURN n"

        async with self.driver.session() as session:
            result = await session.run(query, node_id=node_id)
            record = await result.single()

            if not record:
                return None

            node = record["n"]
            props = dict(node)
            node_type = props.pop("type", "unknown")
            props.pop("id", None)

            return GraphNode(node_type=node_type, node_id=node_id, properties=props)

    async def query(
        self,
        pattern: str,
        params: dict | None = None,
    ) -> GraphQueryResult:
        """
        Execute a Cypher query.

        Args:
            pattern: Cypher query string
            params: Query parameters

        Returns:
            GraphQueryResult with matching nodes and edges
        """
        async with self.driver.session() as session:
            result = await session.run(pattern, **(params or {}))
            records = await result.data()

            nodes = []
            edges = []

            for record in records:
                for key, value in record.items():
                    # Neo4j returns node and relationship objects
                    if hasattr(value, "labels"):  # It's a node
                        props = dict(value)
                        node_type = props.pop("type", "unknown")
                        node_id = props.pop("id", key)
                        nodes.append(GraphNode(node_type, node_id, props))

                    elif hasattr(value, "type"):  # It's a relationship
                        # Extract edge data from relationship
                        props = dict(value)
                        rel_type = props.pop("type", "related")
                        # Need to get start/end node IDs
                        from_id = value.start_node.get("id", "")
                        to_id = value.end_node.get("id", "")
                        edges.append(GraphEdge(from_id, to_id, rel_type, props))

            return GraphQueryResult(nodes=nodes, edges=edges)

    async def get_related(
        self,
        node_id: str,
        relationship: str | None = None,
        direction: str = "outgoing",
        depth: int = 1,
    ) -> list[GraphNode]:
        """Get nodes related to the given node."""
        # Build Cypher pattern based on direction
        if direction == "outgoing":
            pattern = "-[r]->".join([""] * (depth + 1))
            cypher = f"MATCH (n {{id: $node_id}}){pattern}(m)"
        elif direction == "incoming":
            pattern = "<-[r]-".join([""] * (depth + 1))
            cypher = f"MATCH (n {{id: $node_id}}){pattern}(m)"
        else:  # both
            pattern = "-[r]-".join([""] * (depth + 1))
            cypher = f"MATCH (n {{id: $node_id}}){pattern}(m)"

        # Add relationship filter if specified
        if relationship:
            cypher = cypher.replace("[r]", f"[r {{type: $relationship}}]")

        cypher += " RETURN DISTINCT m"

        params = {"node_id": node_id}
        if relationship:
            params["relationship"] = relationship

        async with self.driver.session() as session:
            result = await session.run(cypher, **params)
            records = await result.data()

            nodes = []
            for record in records:
                node = record["m"]
                props = dict(node)
                node_type = props.pop("type", "unknown")
                node_id_val = props.pop("id", "")
                nodes.append(GraphNode(node_type, node_id_val, props))

            return nodes

    async def delete_node(self, node_id: str) -> None:
        """Delete a node and all its edges."""
        query = "MATCH (n {id: $node_id}) DETACH DELETE n"

        async with self.driver.session() as session:
            await session.run(query, node_id=node_id)

    async def close(self) -> None:
        """Close Neo4j driver connection."""
        if self.driver:
            await self.driver.close()
            self.driver = None
