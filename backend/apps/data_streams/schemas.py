"""
Pydantic schemas for DataStream API.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from ninja import Schema


class DataStreamCreate(Schema):
    """Schema for creating a data stream."""
    source_type: str
    payload: Dict[str, Any]
    raw_data: Optional[Dict[str, Any]] = None


class DataStreamResponse(Schema):
    """Schema for data stream response."""
    id: UUID
    source_type: str
    payload: Dict[str, Any]
    status: str
    created_at: datetime
    processed_at: Optional[datetime] = None
    error_message: Optional[str] = None

    @staticmethod
    def resolve_id(obj):
        return obj.id


class DataStreamListResponse(Schema):
    """Schema for paginated data stream list."""
    items: List[DataStreamResponse]
    total: int
    page: int
    pages: int


class DataStreamFilter(Schema):
    """Schema for filtering data streams."""
    source_type: Optional[str] = None
    status: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
