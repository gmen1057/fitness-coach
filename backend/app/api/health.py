"""
Health check endpoints for monitoring service status.
"""
import logging
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


class RAGHealthResponse(BaseModel):
    """RAG health check response"""
    rag_enabled: bool
    rag_provider: str | None = None
    embedding_provider: str | None = None
    embedding_dimensions: int | None = None
    status: str  # "healthy", "degraded", "unavailable"
    message: str | None = None


@router.get("/health/rag", response_model=RAGHealthResponse)
async def rag_health_check():
    """
    Check RAG subsystem health.

    Returns status of embedding and RAG providers.
    Useful for debugging RAG setup issues.
    """
    from app.config import get_settings
    from app.providers import get_embedding_provider, get_rag_provider

    settings = get_settings()

    result = RAGHealthResponse(
        rag_enabled=False,
        status="unavailable",
        message="RAG not configured"
    )

    # Check if RAG is configured
    if settings.rag_provider == "none" or settings.embedding_provider == "none":
        result.message = "RAG disabled in config (FITNESS_RAG_PROVIDER=none or FITNESS_EMBEDDING_PROVIDER=none)"
        return result

    result.rag_provider = settings.rag_provider
    result.embedding_provider = settings.embedding_provider

    # Check embedding provider
    try:
        embedding = get_embedding_provider()
        if embedding:
            result.embedding_dimensions = embedding.dimensions
            result.rag_enabled = True
        else:
            result.status = "degraded"
            result.message = "Embedding provider failed to initialize"
            return result
    except Exception as e:
        result.status = "degraded"
        result.message = f"Embedding provider error: {str(e)}"
        logger.error(f"Embedding health check failed: {e}")
        return result

    # Check RAG provider
    try:
        rag = await get_rag_provider()
        if rag:
            result.status = "healthy"
            result.message = "All RAG components operational"
        else:
            result.status = "degraded"
            result.message = "RAG provider failed to initialize"
    except Exception as e:
        result.status = "degraded"
        result.message = f"RAG provider error: {str(e)}"
        logger.error(f"RAG health check failed: {e}")

    return result
