"""
PostgreSQL + pgvector RAG provider.

Features:
- HNSW index for fast approximate nearest neighbor search
- SQL injection prevention via whitelist validation
- Connection pooling with timeout and recycling
- JSONB metadata storage
"""
import json
from typing import TYPE_CHECKING

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine

if TYPE_CHECKING:
    from ..protocols import SearchResult

# SQL INJECTION PREVENTION: Allowed collection names
ALLOWED_COLLECTIONS = {"fitness_memory", "workout_embeddings", "chat_history"}


class PgVectorRAG:
    """
    PostgreSQL + pgvector RAG provider.

    Uses HNSW index for efficient vector similarity search.
    Connection pooling optimized for async workloads.
    """

    def __init__(self, database_url: str, collection: str, dimensions: int):
        """
        Initialize pgvector provider.

        Args:
            database_url: PostgreSQL connection string (asyncpg)
            collection: Table name for vector storage
            dimensions: Embedding vector dimensions

        Raises:
            ValueError: If collection name not in whitelist
        """
        # SQL INJECTION PREVENTION: Validate collection name
        if collection not in ALLOWED_COLLECTIONS:
            raise ValueError(
                f"Invalid collection name: {collection}. "
                f"Allowed: {', '.join(ALLOWED_COLLECTIONS)}"
            )

        self.database_url = database_url
        self.collection = collection
        self.dimensions = dimensions
        self.engine: AsyncEngine | None = None

    async def initialize(self) -> None:
        """
        Initialize database connection and create table with HNSW index.

        Creates:
        - Vector extension (pgvector)
        - Table with id, content, embedding, metadata columns
        - HNSW index with optimized parameters
        """
        # Create engine with connection pooling
        self.engine = create_async_engine(
            self.database_url,
            pool_size=5,  # Minimum connections
            max_overflow=10,  # Max extra connections
            pool_timeout=30,  # Wait time before giving up
            pool_recycle=1800,  # Recycle connections after 30 min
            echo=False,
        )

        async with self.engine.begin() as conn:
            # Enable pgvector extension
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

            # Create table (collection name validated in __init__)
            create_table_sql = f"""
                CREATE TABLE IF NOT EXISTS {self.collection} (
                    id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    embedding vector({self.dimensions}) NOT NULL,
                    metadata JSONB,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """
            await conn.execute(text(create_table_sql))

            # Create HNSW index for fast similarity search
            # m=24: More accurate but larger index
            # ef_construction=100: Build quality (higher = slower build, better recall)
            create_index_sql = f"""
                CREATE INDEX IF NOT EXISTS {self.collection}_hnsw_idx
                ON {self.collection}
                USING hnsw (embedding vector_cosine_ops)
                WITH (m = 24, ef_construction = 100)
            """
            await conn.execute(text(create_index_sql))

    async def store(
        self,
        id: str,
        content: str,
        embedding: list[float],
        metadata: dict | None = None,
    ) -> None:
        """
        Store or update document with embedding.

        Args:
            id: Unique document identifier
            content: Document text content
            embedding: Vector embedding
            metadata: Optional metadata dict
        """
        if not self.engine:
            raise RuntimeError("RAG provider not initialized. Call initialize() first.")

        # Convert metadata to JSON
        metadata_json = json.dumps(metadata) if metadata else None

        # Convert embedding to pgvector format
        embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"

        # Use parameterized query to prevent SQL injection
        sql = f"""
            INSERT INTO {self.collection} (id, content, embedding, metadata)
            VALUES (:id, :content, :embedding::vector, :metadata::jsonb)
            ON CONFLICT (id) DO UPDATE SET
                content = EXCLUDED.content,
                embedding = EXCLUDED.embedding,
                metadata = EXCLUDED.metadata,
                created_at = NOW()
        """

        async with self.engine.begin() as conn:
            await conn.execute(
                text(sql),
                {
                    "id": id,
                    "content": content,
                    "embedding": embedding_str,
                    "metadata": metadata_json,
                },
            )

    async def search(
        self,
        query_embedding: list[float],
        limit: int = 5,
        filter: dict | None = None,
    ) -> list["SearchResult"]:
        """
        Search for similar documents using cosine similarity.

        Args:
            query_embedding: Query vector
            limit: Maximum number of results (default: 5)
            filter: Optional metadata filters (not implemented yet)

        Returns:
            List of SearchResult ordered by similarity (highest first)
        """
        if not self.engine:
            raise RuntimeError("RAG provider not initialized. Call initialize() first.")

        # Convert embedding to pgvector format
        embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

        # Cosine similarity search (1 - cosine_distance)
        # Note: We use 1 - (<=> operator) to get similarity score
        # where higher = more similar
        sql = f"""
            SELECT
                id,
                content,
                1 - (embedding <=> :query_embedding::vector) AS score,
                metadata
            FROM {self.collection}
            ORDER BY embedding <=> :query_embedding::vector
            LIMIT :limit
        """

        async with self.engine.connect() as conn:
            result = await conn.execute(
                text(sql),
                {
                    "query_embedding": embedding_str,
                    "limit": limit,
                },
            )

            # Import here to avoid circular dependency
            from ..protocols import SearchResult

            results = []
            for row in result:
                metadata = json.loads(row.metadata) if row.metadata else None
                results.append(
                    SearchResult(
                        id=row.id,
                        content=row.content,
                        score=float(row.score),
                        metadata=metadata,
                    )
                )

            return results

    async def delete(self, id: str) -> None:
        """
        Delete document by ID.

        Args:
            id: Document identifier to delete
        """
        if not self.engine:
            raise RuntimeError("RAG provider not initialized. Call initialize() first.")

        sql = f"DELETE FROM {self.collection} WHERE id = :id"

        async with self.engine.begin() as conn:
            await conn.execute(text(sql), {"id": id})

    async def close(self) -> None:
        """Cleanup database connections."""
        if self.engine:
            await self.engine.dispose()
            self.engine = None
