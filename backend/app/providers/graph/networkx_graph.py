"""
Lightweight in-memory knowledge graph using NetworkX.

Persists to JSON file for simplicity. Good for single-user deployments.
No external database required.
"""
import asyncio
import json
from pathlib import Path
from typing import Any

import networkx as nx

from .protocols import GraphEdge, GraphNode, GraphQueryResult


class NetworkXGraphProvider:
    """
    Lightweight knowledge graph using NetworkX with JSON persistence.

    Nodes and edges are stored in a directed graph with attributes.
    Graph is loaded from/saved to a JSON file for persistence.
    """

    def __init__(self, storage_path: str | Path = "data/fitness_graph.json"):
        """
        Initialize NetworkX graph provider.

        Args:
            storage_path: Path to JSON file for persistence
        """
        self.storage_path = Path(storage_path)
        self.graph: nx.DiGraph = nx.DiGraph()
        self._initialized = False

    async def initialize(self) -> None:
        """Load graph from JSON file if it exists, otherwise initialize with fitness knowledge."""
        if self._initialized:
            return

        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        # Check if file exists and has content
        if self.storage_path.exists() and self.storage_path.stat().st_size > 0:
            await self._load_from_file()
        else:
            # Initialize with basic fitness knowledge
            await self._initialize_fitness_knowledge()
            await self._save_to_file()

        self._initialized = True

    async def _load_from_file(self) -> None:
        """Load graph from JSON file."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._sync_load_from_file)

    def _sync_load_from_file(self) -> None:
        """Synchronous load from file."""
        with open(self.storage_path, encoding="utf-8") as f:
            data = json.load(f)

        # Reconstruct graph
        for node in data.get("nodes", []):
            self.graph.add_node(
                node["id"],
                node_type=node["type"],
                **node.get("properties", {}),
            )

        for edge in data.get("edges", []):
            self.graph.add_edge(
                edge["from_id"],
                edge["to_id"],
                relationship=edge["relationship"],
                **edge.get("properties", {}),
            )

    async def _save_to_file(self) -> None:
        """Save graph to JSON file."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._sync_save_to_file)

    def _sync_save_to_file(self) -> None:
        """Synchronous save to file."""
        # Serialize nodes
        nodes = []
        for node_id, attrs in self.graph.nodes(data=True):
            attrs_copy = dict(attrs)
            node_type = attrs_copy.pop("node_type", "unknown")
            nodes.append({
                "id": node_id,
                "type": node_type,
                "properties": attrs_copy,
            })

        # Serialize edges
        edges = []
        for from_id, to_id, attrs in self.graph.edges(data=True):
            attrs_copy = dict(attrs)
            relationship = attrs_copy.pop("relationship", "related")
            edges.append({
                "from_id": from_id,
                "to_id": to_id,
                "relationship": relationship,
                "properties": attrs_copy,
            })

        data = {"nodes": nodes, "edges": edges}

        with open(self.storage_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    async def _initialize_fitness_knowledge(self) -> None:
        """Pre-populate graph with common exercise knowledge."""
        # Muscle groups
        muscle_groups = [
            "chest", "back", "shoulders", "biceps", "triceps",
            "forearms", "abs", "obliques", "quads", "hamstrings",
            "glutes", "calves", "traps", "lats", "delts",
        ]
        for mg in muscle_groups:
            await self.add_node("muscle_group", mg, {"name": mg.title()})

        # Common exercises with their target muscles
        exercises = [
            # Chest
            ("push_up", "Push-up", ["chest", "triceps", "shoulders"]),
            ("bench_press", "Bench Press", ["chest", "triceps", "shoulders"]),
            ("dumbbell_fly", "Dumbbell Fly", ["chest"]),

            # Back
            ("pull_up", "Pull-up", ["lats", "back", "biceps"]),
            ("barbell_row", "Barbell Row", ["back", "lats", "biceps"]),
            ("deadlift", "Deadlift", ["back", "hamstrings", "glutes", "traps"]),

            # Shoulders
            ("overhead_press", "Overhead Press", ["delts", "shoulders", "triceps"]),
            ("lateral_raise", "Lateral Raise", ["delts", "shoulders"]),

            # Arms
            ("bicep_curl", "Bicep Curl", ["biceps"]),
            ("tricep_dip", "Tricep Dip", ["triceps"]),

            # Legs
            ("squat", "Squat", ["quads", "glutes", "hamstrings"]),
            ("leg_press", "Leg Press", ["quads", "glutes"]),
            ("leg_curl", "Leg Curl", ["hamstrings"]),
            ("calf_raise", "Calf Raise", ["calves"]),

            # Core
            ("plank", "Plank", ["abs", "obliques"]),
            ("crunch", "Crunch", ["abs"]),
        ]

        for exercise_id, exercise_name, targets in exercises:
            await self.add_node("exercise", exercise_id, {"name": exercise_name})
            for muscle in targets:
                await self.add_edge(exercise_id, muscle, "targets", {"primary": muscle in targets[:1]})

        # Exercise progressions
        progressions = [
            ("push_up", "diamond_push_up", "Diamond Push-up"),
            ("diamond_push_up", "archer_push_up", "Archer Push-up"),
            ("pull_up", "weighted_pull_up", "Weighted Pull-up"),
            ("squat", "pistol_squat", "Pistol Squat"),
            ("plank", "side_plank", "Side Plank"),
        ]

        for base_id, advanced_id, advanced_name in progressions:
            await self.add_node("exercise", advanced_id, {"name": advanced_name})
            await self.add_edge(base_id, advanced_id, "progresses_to", {"difficulty_increase": 1})

        # Exercise alternatives (same muscle groups, different movement)
        alternatives = [
            ("bench_press", "push_up", "bodyweight alternative"),
            ("barbell_row", "pull_up", "vertical pull alternative"),
            ("leg_press", "squat", "free weight alternative"),
        ]

        for ex1, ex2, reason in alternatives:
            await self.add_edge(ex1, ex2, "alternative_to", {"reason": reason})

    async def add_node(
        self,
        node_type: str,
        node_id: str,
        properties: dict | None = None,
    ) -> GraphNode:
        """Add or update a node in the graph."""
        attrs = {"node_type": node_type}
        if properties:
            attrs.update(properties)

        self.graph.add_node(node_id, **attrs)
        await self._save_to_file()

        return GraphNode(node_type=node_type, node_id=node_id, properties=properties or {})

    async def add_edge(
        self,
        from_id: str,
        to_id: str,
        relationship: str,
        properties: dict | None = None,
    ) -> GraphEdge:
        """Add or update an edge between two nodes."""
        attrs = {"relationship": relationship}
        if properties:
            attrs.update(properties)

        self.graph.add_edge(from_id, to_id, **attrs)
        await self._save_to_file()

        return GraphEdge(
            from_id=from_id,
            to_id=to_id,
            relationship=relationship,
            properties=properties or {},
        )

    async def get_node(self, node_id: str) -> GraphNode | None:
        """Get a node by ID."""
        if node_id not in self.graph:
            return None

        attrs = dict(self.graph.nodes[node_id])
        node_type = attrs.pop("node_type", "unknown")

        return GraphNode(node_type=node_type, node_id=node_id, properties=attrs)

    async def query(
        self,
        pattern: str,
        params: dict | None = None,
    ) -> GraphQueryResult:
        """
        Execute a simple graph pattern query.

        Pattern format: "node_type->relationship->node_type"
        Example: "exercise->targets->muscle_group"

        Returns all matching paths.
        """
        parts = pattern.split("->")
        if len(parts) != 3:
            return GraphQueryResult(nodes=[], edges=[])

        source_type, rel, target_type = parts

        matching_nodes = []
        matching_edges = []

        for from_id, to_id, edge_data in self.graph.edges(data=True):
            if edge_data.get("relationship") != rel:
                continue

            from_node = self.graph.nodes[from_id]
            to_node = self.graph.nodes[to_id]

            if from_node.get("node_type") == source_type and to_node.get("node_type") == target_type:
                # Build nodes
                from_props = {k: v for k, v in from_node.items() if k != "node_type"}
                to_props = {k: v for k, v in to_node.items() if k != "node_type"}

                matching_nodes.append(GraphNode(source_type, from_id, from_props))
                matching_nodes.append(GraphNode(target_type, to_id, to_props))

                # Build edge
                edge_props = {k: v for k, v in edge_data.items() if k != "relationship"}
                matching_edges.append(GraphEdge(from_id, to_id, rel, edge_props))

        # Deduplicate nodes
        unique_nodes = {n.node_id: n for n in matching_nodes}
        return GraphQueryResult(nodes=list(unique_nodes.values()), edges=matching_edges)

    async def get_related(
        self,
        node_id: str,
        relationship: str | None = None,
        direction: str = "outgoing",
        depth: int = 1,
    ) -> list[GraphNode]:
        """Get nodes related to the given node."""
        if node_id not in self.graph:
            return []

        visited = set([node_id])  # Start with source node visited
        queue = [(node_id, 0)]
        related = []

        while queue:
            current_id, current_depth = queue.pop(0)

            if current_depth >= depth:
                # At max depth, just collect neighbors without traversing further
                neighbors = []
                if direction in ("outgoing", "both"):
                    for _, target, edge_data in self.graph.out_edges(current_id, data=True):
                        if relationship is None or edge_data.get("relationship") == relationship:
                            if target not in visited:
                                neighbors.append(target)

                if direction in ("incoming", "both"):
                    for source, _, edge_data in self.graph.in_edges(current_id, data=True):
                        if relationship is None or edge_data.get("relationship") == relationship:
                            if source not in visited:
                                neighbors.append(source)

                for neighbor_id in neighbors:
                    visited.add(neighbor_id)
                    node_data = dict(self.graph.nodes[neighbor_id])
                    node_type = node_data.pop("node_type", "unknown")
                    related.append(GraphNode(node_type, neighbor_id, node_data))

                continue

            # Get neighbors for traversal
            neighbors = []
            if direction in ("outgoing", "both"):
                for _, target, edge_data in self.graph.out_edges(current_id, data=True):
                    if relationship is None or edge_data.get("relationship") == relationship:
                        neighbors.append(target)

            if direction in ("incoming", "both"):
                for source, _, edge_data in self.graph.in_edges(current_id, data=True):
                    if relationship is None or edge_data.get("relationship") == relationship:
                        neighbors.append(source)

            for neighbor_id in neighbors:
                if neighbor_id not in visited:
                    visited.add(neighbor_id)
                    node_data = dict(self.graph.nodes[neighbor_id])
                    node_type = node_data.pop("node_type", "unknown")
                    related.append(GraphNode(node_type, neighbor_id, node_data))
                    queue.append((neighbor_id, current_depth + 1))

        return related

    async def delete_node(self, node_id: str) -> None:
        """Delete a node and all its edges."""
        if node_id in self.graph:
            self.graph.remove_node(node_id)
            await self._save_to_file()

    async def close(self) -> None:
        """Cleanup resources (save final state)."""
        if self._initialized:
            await self._save_to_file()
