"""
API Dependencies - Shared validation and dependency injection.

Provides pack validation and other common dependencies for API endpoints.
"""

from fastapi import HTTPException, Query
from typing import Optional

# Valid packs in the system
VALID_PACKS = ["treasury", "wealth"]


def validate_pack(pack: str) -> str:
    """
    Validate that a pack name is valid.

    Args:
        pack: Pack name to validate

    Returns:
        The validated pack name

    Raises:
        HTTPException: If pack is invalid
    """
    if pack not in VALID_PACKS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid pack '{pack}'. Valid packs: {', '.join(VALID_PACKS)}"
        )
    return pack


def get_required_pack(pack: str = Query(..., description="Pack name (treasury or wealth)")) -> str:
    """
    FastAPI dependency that requires and validates pack parameter.

    Usage:
        @router.get("/items")
        def list_items(pack: str = Depends(get_required_pack)):
            ...
    """
    return validate_pack(pack)


def get_optional_pack(pack: Optional[str] = Query(None, description="Pack name filter")) -> Optional[str]:
    """
    FastAPI dependency for optional pack parameter with validation.

    Usage:
        @router.get("/items")
        def list_items(pack: Optional[str] = Depends(get_optional_pack)):
            ...
    """
    if pack is not None:
        return validate_pack(pack)
    return None
