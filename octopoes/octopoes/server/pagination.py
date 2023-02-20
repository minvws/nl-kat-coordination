"""Pagination helpers."""

from typing import Any, List, Optional

from fastapi import Request
from pydantic import BaseModel


class PaginatedResponse(BaseModel):
    """Pagination model."""

    count: int
    next: Optional[str]
    previous: Optional[str]
    results: List[Any]


def create_next_url(request: Request, offset: int, limit: int, count: int) -> Optional[str]:
    """Create the next URL for pagination."""
    if offset + limit <= count:
        return str(request.url.include_query_params(limit=limit, offset=offset + limit))

    return None


def create_previous_url(request: Request, offset: int, limit: int) -> Optional[str]:
    """Create the previous URL for pagination."""
    if offset - limit >= 0:
        return str(request.url.include_query_params(limit=limit, offset=offset - limit))

    return None


def paginate(request: Request, items: List[Any], count: int, offset: int, limit: int) -> PaginatedResponse:
    """Paginate the results."""
    return PaginatedResponse(
        count=count,
        next=create_next_url(request, offset, limit, count),
        previous=create_previous_url(request, offset, limit),
        results=items,
    )
