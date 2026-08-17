"""
Pydantic schemas for Workspace API.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from ninja import Schema


class TaskCreate(Schema):
    title: str
    description: str = ""
    status: str = "todo"
    priority: str = "medium"
    due_date: Optional[datetime] = None
    tags: List[str] = []
    position: int = 0


class TaskUpdate(Schema):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    due_date: Optional[datetime] = None
    tags: Optional[List[str]] = None
    position: Optional[int] = None


class TaskResponse(Schema):
    id: UUID
    title: str
    description: str
    status: str
    priority: str
    due_date: Optional[datetime]
    tags: List[str]
    position: int
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def resolve_id(obj):
        return obj.id


class EventCreate(Schema):
    title: str
    description: str = ""
    location: str = ""
    start_time: datetime
    end_time: datetime
    all_day: bool = False
    recurrence: str = "none"
    reminder_minutes: int = 30
    color: str = "#3b82f6"


class EventUpdate(Schema):
    title: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    all_day: Optional[bool] = None
    recurrence: Optional[str] = None
    reminder_minutes: Optional[int] = None
    color: Optional[str] = None


class EventResponse(Schema):
    id: UUID
    title: str
    description: str
    location: str
    start_time: datetime
    end_time: datetime
    all_day: bool
    recurrence: str
    reminder_minutes: int
    color: str
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def resolve_id(obj):
        return obj.id


class NewsFeedCreate(Schema):
    name: str
    url: str
    feed_type: str = "rss"
    scrape_interval_minutes: int = 60


class NewsFeedResponse(Schema):
    id: UUID
    name: str
    url: str
    feed_type: str
    is_active: bool
    scrape_interval_minutes: int
    last_scraped: Optional[datetime]
    created_at: datetime

    @staticmethod
    def resolve_id(obj):
        return obj.id


class ArticleResponse(Schema):
    id: UUID
    title: str
    url: str
    content: str
    summary: str
    image_url: str = ""
    author: str
    published_at: Optional[datetime]
    is_read: bool
    is_bookmarked: bool
    created_at: datetime

    @staticmethod
    def resolve_id(obj):
        return obj.id


class WidgetCreate(Schema):
    widget_type: str
    title: str
    position_x: int = 0
    position_y: int = 0
    width: int = 1
    height: int = 1
    config: Dict[str, Any] = {}


class WidgetUpdate(Schema):
    title: Optional[str] = None
    position_x: Optional[int] = None
    position_y: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None
    is_visible: Optional[bool] = None
    config: Optional[Dict[str, Any]] = None


class WidgetResponse(Schema):
    id: UUID
    widget_type: str
    title: str
    position_x: int
    position_y: int
    width: int
    height: int
    is_visible: bool
    config: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def resolve_id(obj):
        return obj.id


class NoteCreate(Schema):
    title: str
    content: str = ""
    format: str = "note"
    tags: List[str] = []
    is_pinned: bool = False


class NoteUpdate(Schema):
    title: Optional[str] = None
    content: Optional[str] = None
    format: Optional[str] = None
    tags: Optional[List[str]] = None
    is_pinned: Optional[bool] = None


class NoteResponse(Schema):
    id: UUID
    title: str
    content: str
    format: str
    tags: List[str]
    is_pinned: bool
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def resolve_id(obj):
        return obj.id


class NoteGenerateRequest(Schema):
    target_format: str = "presentation"
    style: str = "professional"
    max_length: Optional[int] = None


class GeneratedDocumentUpdate(Schema):
    title: Optional[str] = None
    style: Optional[str] = None


class GeneratedDocumentResponse(Schema):
    id: UUID
    note_id: UUID
    title: str
    content: str
    doc_format: str
    file_format: str
    style: str
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def resolve_id(obj):
        return obj.id

    @staticmethod
    def resolve_note_id(obj):
        return obj.note_id


class TriggerCreate(Schema):
    name: str
    trigger_type: str = "time_based"
    trigger_time: Optional[datetime] = None
    trigger_minutes_before: Optional[int] = None
    message: str
    action_type: str = "notification"


class TriggerResponse(Schema):
    id: UUID
    name: str
    trigger_type: str
    trigger_time: Optional[datetime]
    trigger_minutes_before: Optional[int]
    message: str
    action_type: str
    is_active: bool
    last_fired: Optional[datetime]
    created_at: datetime

    @staticmethod
    def resolve_id(obj):
        return obj.id
