"""
Workspace API endpoints for ML-Auditor.
Tasks, Calendar, News, Widgets, Triggers.
"""

from django.utils import timezone
from django.core.cache import cache
from ninja import Router, Query
from ninja.errors import HttpError

from .models import Task, CalendarEvent, NewsFeed, NewsArticle, WorkspaceWidget, Trigger
from .schemas import (
    TaskCreate, TaskUpdate, TaskResponse,
    EventCreate, EventUpdate, EventResponse,
    NewsFeedCreate, NewsFeedResponse, ArticleResponse,
    WidgetCreate, WidgetUpdate, WidgetResponse,
    TriggerCreate, TriggerResponse,
)

router = Router()

PAGE_SIZE = 20


# ─── Tasks (Wall of Work) ───────────────────────────────────────────

@router.get("/tasks", response=list[TaskResponse])
def list_tasks(
    request,
    status: str = Query(None),
    priority: str = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(PAGE_SIZE, ge=1, le=100),
):
    """List tasks for current user."""
    qs = Task.objects.filter(user=request.auth).select_related("user")
    if status:
        qs = qs.filter(status=status)
    if priority:
        qs = qs.filter(priority=priority)
    offset = (page - 1) * page_size
    return list(qs[offset : offset + page_size])


@router.post("/tasks", response=TaskResponse)
def create_task(request, payload: TaskCreate):
    """Create a new task."""
    task = Task.objects.create(
        user=request.auth,
        **payload.dict(),
    )
    return task


@router.get("/tasks/{task_id}", response=TaskResponse)
def get_task(request, task_id: str):
    """Get task by ID."""
    try:
        return Task.objects.get(id=task_id, user=request.auth)
    except Task.DoesNotExist:
        raise HttpError(404, "Task not found")


@router.put("/tasks/{task_id}", response=TaskResponse)
def update_task(request, task_id: str, payload: TaskUpdate):
    """Update a task."""
    try:
        task = Task.objects.get(id=task_id, user=request.auth)
        for field, value in payload.dict(exclude_unset=True).items():
            setattr(task, field, value)
        task.save()
        return task
    except Task.DoesNotExist:
        raise HttpError(404, "Task not found")


@router.delete("/tasks/{task_id}")
def delete_task(request, task_id: str):
    """Delete a task."""
    try:
        Task.objects.get(id=task_id, user=request.auth).delete()
        return {"success": True}
    except Task.DoesNotExist:
        raise HttpError(404, "Task not found")


@router.put("/tasks/{task_id}/move")
def move_task(request, task_id: str, status: str, position: int = 0):
    """Move task to a different status column."""
    try:
        task = Task.objects.get(id=task_id, user=request.auth)
        task.status = status
        task.position = position
        task.save()
        return {"success": True, "status": status}
    except Task.DoesNotExist:
        raise HttpError(404, "Task not found")


# ─── Calendar Events ─────────────────────────────────────────────────

@router.get("/events", response=list[EventResponse])
def list_events(
    request,
    start: str = Query(None),
    end: str = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(PAGE_SIZE, ge=1, le=100),
):
    """List calendar events for current user."""
    qs = CalendarEvent.objects.filter(user=request.auth).select_related("user")
    if start:
        qs = qs.filter(start_time__gte=start)
    if end:
        qs = qs.filter(end_time__lte=end)
    offset = (page - 1) * page_size
    return list(qs[offset : offset + page_size])


@router.post("/events", response=EventResponse)
def create_event(request, payload: EventCreate):
    """Create a new calendar event."""
    event = CalendarEvent.objects.create(
        user=request.auth,
        **payload.dict(),
    )
    return event


@router.get("/events/{event_id}", response=EventResponse)
def get_event(request, event_id: str):
    """Get event by ID."""
    try:
        return CalendarEvent.objects.get(id=event_id, user=request.auth)
    except CalendarEvent.DoesNotExist:
        raise HttpError(404, "Event not found")


@router.put("/events/{event_id}", response=EventResponse)
def update_event(request, event_id: str, payload: EventUpdate):
    """Update a calendar event."""
    try:
        event = CalendarEvent.objects.get(id=event_id, user=request.auth)
        for field, value in payload.dict(exclude_unset=True).items():
            setattr(event, field, value)
        event.save()
        return event
    except CalendarEvent.DoesNotExist:
        raise HttpError(404, "Event not found")


@router.delete("/events/{event_id}")
def delete_event(request, event_id: str):
    """Delete a calendar event."""
    try:
        CalendarEvent.objects.get(id=event_id, user=request.auth).delete()
        return {"success": True}
    except CalendarEvent.DoesNotExist:
        raise HttpError(404, "Event not found")


@router.get("/events/today", response=list[EventResponse])
def today_events(request):
    """Get today's events."""
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timezone.timedelta(days=1)
    return list(
        CalendarEvent.objects.filter(
            user=request.auth,
            start_time__gte=today_start,
            end_time__lte=today_end,
        )
    )


# ─── News Feeds ──────────────────────────────────────────────────────

@router.get("/feeds", response=list[NewsFeedResponse])
def list_feeds(request):
    """List news feeds for current user."""
    return list(NewsFeed.objects.filter(user=request.auth))


@router.post("/feeds", response=NewsFeedResponse)
def create_feed(request, payload: NewsFeedCreate):
    """Create a new news feed."""
    feed = NewsFeed.objects.create(
        user=request.auth,
        **payload.dict(),
    )
    return feed


@router.delete("/feeds/{feed_id}")
def delete_feed(request, feed_id: str):
    """Delete a news feed."""
    try:
        NewsFeed.objects.get(id=feed_id, user=request.auth).delete()
        return {"success": True}
    except NewsFeed.DoesNotExist:
        raise HttpError(404, "Feed not found")


@router.get("/feeds/{feed_id}/articles", response=list[ArticleResponse])
def list_articles(request, feed_id: str, limit: int = Query(20)):
    """List articles from a feed."""
    return list(
        NewsArticle.objects.filter(feed_id=feed_id, feed__user=request.auth)[:limit]
    )


@router.get("/articles", response=list[ArticleResponse])
def all_articles(
    request,
    is_read: bool = Query(None),
    is_bookmarked: bool = Query(None),
    limit: int = Query(50, ge=1, le=200),
):
    """List all articles across feeds."""
    qs = NewsArticle.objects.filter(feed__user=request.auth).select_related("feed")
    if is_read is not None:
        qs = qs.filter(is_read=is_read)
    if is_bookmarked is not None:
        qs = qs.filter(is_bookmarked=is_bookmarked)
    return list(qs[:limit])


@router.put("/articles/{article_id}/read")
def mark_article_read(request, article_id: str):
    """Mark article as read."""
    try:
        article = NewsArticle.objects.get(id=article_id, feed__user=request.auth)
        article.is_read = True
        article.save()
        return {"success": True}
    except NewsArticle.DoesNotExist:
        raise HttpError(404, "Article not found")


@router.put("/articles/{article_id}/bookmark")
def toggle_bookmark(request, article_id: str):
    """Toggle article bookmark."""
    try:
        article = NewsArticle.objects.get(id=article_id, feed__user=request.auth)
        article.is_bookmarked = not article.is_bookmarked
        article.save()
        return {"success": True, "is_bookmarked": article.is_bookmarked}
    except NewsArticle.DoesNotExist:
        raise HttpError(404, "Article not found")


# ─── Widgets (Bento Grid) ───────────────────────────────────────────

@router.get("/widgets", response=list[WidgetResponse])
def list_widgets(request):
    """List user's widgets."""
    return list(WorkspaceWidget.objects.filter(user=request.auth))


@router.post("/widgets", response=WidgetResponse)
def create_widget(request, payload: WidgetCreate):
    """Add a widget to the dashboard."""
    widget = WorkspaceWidget.objects.create(
        user=request.auth,
        **payload.dict(),
    )
    return widget


@router.put("/widgets/{widget_id}", response=WidgetResponse)
def update_widget(request, widget_id: str, payload: WidgetUpdate):
    """Update widget position/size/config."""
    try:
        widget = WorkspaceWidget.objects.get(id=widget_id, user=request.auth)
        for field, value in payload.dict(exclude_unset=True).items():
            setattr(widget, field, value)
        widget.save()
        return widget
    except WorkspaceWidget.DoesNotExist:
        raise HttpError(404, "Widget not found")


@router.delete("/widgets/{widget_id}")
def delete_widget(request, widget_id: str):
    """Remove a widget."""
    try:
        WorkspaceWidget.objects.get(id=widget_id, user=request.auth).delete()
        return {"success": True}
    except WorkspaceWidget.DoesNotExist:
        raise HttpError(404, "Widget not found")


# ─── Triggers ────────────────────────────────────────────────────────

@router.get("/triggers", response=list[TriggerResponse])
def list_triggers(request):
    """List user's triggers."""
    return list(Trigger.objects.filter(user=request.auth))


@router.post("/triggers", response=TriggerResponse)
def create_trigger(request, payload: TriggerCreate):
    """Create a trigger."""
    trigger = Trigger.objects.create(
        user=request.auth,
        **payload.dict(),
    )
    return trigger


@router.delete("/triggers/{trigger_id}")
def delete_trigger(request, trigger_id: str):
    """Delete a trigger."""
    try:
        Trigger.objects.get(id=trigger_id, user=request.auth).delete()
        return {"success": True}
    except Trigger.DoesNotExist:
        raise HttpError(404, "Trigger not found")
