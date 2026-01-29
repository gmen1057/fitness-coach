"""
Shared API dependencies.

Common FastAPI dependencies used across multiple routers.
"""
from typing import Optional
from uuid import UUID

from fastapi import Header, HTTPException

# Default user ID for single-user mode
# In production, replace with proper authentication
DEFAULT_USER_ID = "00000000-0000-0000-0000-000000000001"


def get_user_id(x_user_id: Optional[str] = Header(None)) -> UUID:
    """
    Get user ID from X-User-ID header or use default.

    For single-user apps, defaults to DEFAULT_USER_ID.
    For multi-user scenarios, implement proper authentication.

    Args:
        x_user_id: Optional user ID from X-User-ID header

    Returns:
        UUID of the user

    Raises:
        HTTPException: If user ID format is invalid
    """
    if x_user_id:
        try:
            return UUID(x_user_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid user ID format")
    return UUID(DEFAULT_USER_ID)
