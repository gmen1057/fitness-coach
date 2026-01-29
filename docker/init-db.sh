#!/bin/bash
# =============================================================================
# PostgreSQL Initialization Script
# =============================================================================
# Runs on first container start to set up database
# Creates pgvector extension and sets up proper permissions

set -e

echo "Initializing database..."

# Create pgvector extension
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    -- Enable pgvector extension for RAG support
    CREATE EXTENSION IF NOT EXISTS vector;

    -- Verify extension
    SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';

    -- Grant necessary permissions
    GRANT ALL PRIVILEGES ON DATABASE "$POSTGRES_DB" TO "$POSTGRES_USER";

    -- Create schema for application
    CREATE SCHEMA IF NOT EXISTS public;
    GRANT ALL ON SCHEMA public TO "$POSTGRES_USER";
    GRANT ALL ON SCHEMA public TO public;
EOSQL

echo "Database initialization completed successfully"
