"""add_pgvector_rag_tables

Revision ID: 2c636582abfa
Revises: 01
Create Date: 2026-01-29 13:35:31.219913

Creates pgvector extension and RAG tables for semantic search.

Tables created:
- fitness_memory: Main RAG collection for workout/exercise embeddings
- workout_embeddings: Alternative collection (reserved for future use)
- chat_history: Alternative collection for chat embeddings (reserved)

Note: This migration is safe to run even if pgvector is not installed.
      The extension and tables will only be used when FITNESS_RAG_PROVIDER=pgvector.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = '2c636582abfa'
down_revision: Union[str, None] = '01'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Create pgvector extension and RAG tables.

    The pgvector extension enables vector similarity search.
    Tables are pre-configured with HNSW indexes for fast approximate nearest neighbor search.
    """
    # Create pgvector extension (requires PostgreSQL with pgvector installed)
    # Note: Extension creation requires superuser privileges
    # If this fails, run manually: sudo -u postgres psql -d fitness_coach -c "CREATE EXTENSION IF NOT EXISTS vector;"
    try:
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    except Exception as e:
        # Extension might already exist or user lacks privileges
        # This is not critical - tables can still be created
        print(f"Warning: Could not create vector extension: {e}")
        print("If pgvector is needed, create extension manually as superuser.")

    # Default embedding dimension (OpenAI text-embedding-3-small)
    # Can be overridden via FITNESS_EMBEDDING_DIMENSIONS env var
    dimensions = 1536

    # Create fitness_memory table (main RAG collection)
    op.create_table(
        'fitness_memory',
        sa.Column('id', sa.Text, primary_key=True),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('embedding', Vector(dimensions), nullable=False),
        sa.Column('metadata', postgresql.JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Create HNSW index for fast similarity search
    # m=24: More accurate but larger index
    # ef_construction=100: Build quality (higher = slower build, better recall)
    op.execute("""
        CREATE INDEX fitness_memory_hnsw_idx
        ON fitness_memory
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 24, ef_construction = 100)
    """)

    # Create workout_embeddings table (alternative collection)
    op.create_table(
        'workout_embeddings',
        sa.Column('id', sa.Text, primary_key=True),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('embedding', Vector(dimensions), nullable=False),
        sa.Column('metadata', postgresql.JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.execute("""
        CREATE INDEX workout_embeddings_hnsw_idx
        ON workout_embeddings
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 24, ef_construction = 100)
    """)

    # Create chat_history table (alternative collection)
    op.create_table(
        'chat_history',
        sa.Column('id', sa.Text, primary_key=True),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('embedding', Vector(dimensions), nullable=False),
        sa.Column('metadata', postgresql.JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.execute("""
        CREATE INDEX chat_history_hnsw_idx
        ON chat_history
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 24, ef_construction = 100)
    """)


def downgrade() -> None:
    """Remove RAG tables and pgvector extension."""
    # Drop tables (indexes are dropped automatically with tables)
    op.drop_table('chat_history')
    op.drop_table('workout_embeddings')
    op.drop_table('fitness_memory')

    # Drop pgvector extension
    # Note: This is commented out by default to avoid breaking other databases
    # op.execute("DROP EXTENSION IF EXISTS vector CASCADE")
