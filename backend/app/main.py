"""
FastAPI application for Open Source Fitness Coach.

A minimalist AI fitness assistant using Claude with tool use.
Features:
- SSE streaming chat with AI agent
- Workout plan management
- Progress tracking
- Rate limiting with slowapi
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.config import get_settings
from app.db import init_db

settings = get_settings()

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.debug else logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Rate limiter
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup/shutdown events.

    Startup:
    - Initialize database (create tables)
    - Log configuration

    Shutdown:
    - Clean up resources
    """
    # Startup
    logger.info("Starting Open Source Fitness Coach API...")
    logger.info(f"AI Provider: {settings.ai_provider}")
    logger.info(f"RAG Provider: {settings.rag_provider}")

    await init_db()
    logger.info("Database initialized")

    yield

    # Shutdown
    logger.info("Shutting down...")


# Create FastAPI app
app = FastAPI(
    title="Open Source Fitness Coach API",
    description="AI-powered fitness assistant with workout planning and progress tracking",
    version="1.0.0",
    lifespan=lifespan,
)

# Add rate limiter state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import and register routers
from app.api import health as health_router
from app.api.fitness import chat as fitness_chat
from app.api.fitness import plans as fitness_plans
from app.api.fitness import workouts as fitness_workouts

app.include_router(fitness_chat.router, prefix="/api/fitness", tags=["fitness-chat"])
app.include_router(fitness_plans.router, prefix="/api/fitness", tags=["fitness-plans"])
app.include_router(fitness_workouts.router, prefix="/api/fitness", tags=["fitness-workouts"])
app.include_router(health_router.router, prefix="/api")


@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "app": "Open Source Fitness Coach",
        "version": "1.0.0",
        "status": "healthy",
        "ai_provider": settings.ai_provider,
        "rag_provider": settings.rag_provider
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/health/ready")
async def readiness_check(request: Request):
    """
    Readiness check for k8s/docker.

    Checks that the app is ready to serve traffic.
    """
    # Could add DB connection check here
    return {
        "status": "ready",
        "ai_provider": settings.ai_provider
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
