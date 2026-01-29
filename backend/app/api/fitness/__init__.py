"""
Fitness module API endpoints.

Contains routers for:
- chat: AI assistant with SSE streaming
- plans: Workout plan management
- workouts: Progress tracking and completion
"""
from fastapi import APIRouter

router = APIRouter()
