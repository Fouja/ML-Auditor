"""
Pydantic schemas for Alert API.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from ninja import Schema


class AlertResponse(Schema):
    """Schema for alert response."""
    id: UUID
    title: str
    description: str
    severity: str
    status: str
    source_type: Optional[str] = None
    source_id: Optional[UUID] = None
    action_payload: Optional[Dict[str, Any]] = None
    created_at: datetime
    acknowledged_at: Optional[datetime] = None
    executed_at: Optional[datetime] = None

    @staticmethod
    def resolve_id(obj):
        return obj.id


class AlertUpdate(Schema):
    """Schema for updating alert."""
    status: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    executed_at: Optional[datetime] = None


class AlertListResponse(Schema):
    """Schema for paginated alert list."""
    items: List[AlertResponse]
    total: int
    page: int
    pages: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int


class AlertStats(Schema):
    """Schema for alert statistics."""
    total: int
    pending: int
    acknowledged: int
    executed: int
    dismissed: int
    by_severity: Dict[str, int]
