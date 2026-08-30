"""
Workspace API endpoints for ML-Auditor.
Tasks, Calendar, News, Widgets, Triggers.
"""

from django.utils import timezone
from ninja import Query, Router
from ninja.errors import HttpError

from .models import (
    CalendarEvent,
    GeneratedDocument,
    NewsArticle,
    NewsFeed,
    Note,
    Task,
    TaskReminder,
    Trigger,
    WorkspaceWidget,
)
from .schemas import (
    ArticleResponse,
    EventCreate,
    EventResponse,
    EventUpdate,
    GeneratedDocumentResponse,
    GeneratedDocumentUpdate,
    NewsFeedCreate,
    NewsFeedResponse,
    NoteCreate,
    NoteGenerateRequest,
    NoteResponse,
    NoteUpdate,
    TaskCreate,
    TaskResponse,
    TaskUpdate,
    TriggerCreate,
    TriggerResponse,
    WidgetCreate,
    WidgetResponse,
    WidgetUpdate,
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


@router.get("/tasks/reminders")
def task_reminders(request):
    """Return pending task reminders for the current user.

    - boot: tasks due today that have not been notified yet today.
    - one_hour: tasks due within the next hour that have not had their
      one-hour reminder sent.
    """
    from datetime import timedelta

    user = request.auth
    now = timezone.now()
    today = now.date()
    one_hour_later = now + timedelta(hours=1)

    # Tasks due today (not done) that haven't had a boot reminder today.
    boot_tasks = Task.objects.filter(
        user=user,
        status__in=[Task.Status.TODO, Task.Status.IN_PROGRESS, Task.Status.REVIEW],
        due_date__date=today,
    ).select_related("reminder")

    boot_reminders = []
    for task in boot_tasks:
        reminder, _ = TaskReminder.objects.get_or_create(user=user, task=task)
        if reminder.boot_reminder_sent != today:
            boot_reminders.append({
                "id": str(task.id),
                "title": task.title,
                "due_date": task.due_date.isoformat() if task.due_date else None,
                "type": "boot",
            })
            reminder.boot_reminder_sent = today
            reminder.save(update_fields=["boot_reminder_sent"])

    # Tasks due within the next hour (not done) that haven't had a one-hour reminder.
    one_hour_tasks = Task.objects.filter(
        user=user,
        status__in=[Task.Status.TODO, Task.Status.IN_PROGRESS, Task.Status.REVIEW],
        due_date__gt=now,
        due_date__lte=one_hour_later,
    ).select_related("reminder")

    one_hour_reminders = []
    for task in one_hour_tasks:
        reminder, _ = TaskReminder.objects.get_or_create(user=user, task=task)
        # Only send once per task (or once per day if you prefer more granular).
        if reminder.one_hour_reminder_sent is None or reminder.one_hour_reminder_sent.date() != today:
            one_hour_reminders.append({
                "id": str(task.id),
                "title": task.title,
                "due_date": task.due_date.isoformat() if task.due_date else None,
                "type": "one_hour",
            })
            reminder.one_hour_reminder_sent = now
            reminder.save(update_fields=["one_hour_reminder_sent"])

    return {
        "boot": boot_reminders,
        "one_hour": one_hour_reminders,
    }


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


@router.post("/feeds/{feed_id}/scrape")
def scrape_feed(request, feed_id: str):
    """Manually trigger a scrape of a feed's articles now."""
    from .tasks import _fetch_feed, _summarize_with_llm

    try:
        feed = NewsFeed.objects.get(id=feed_id, user=request.auth)
    except NewsFeed.DoesNotExist:
        raise HttpError(404, "Feed not found")

    from django.utils import timezone

    scraped = 0
    try:
        for article_data in _fetch_feed(feed):
            if NewsArticle.objects.filter(url=article_data["url"]).exists():
                continue
            summary = article_data.get("summary") or ""
            if feed.feed_type == "webpage" or not summary:
                summary = _summarize_with_llm(
                    article_data.get("title", ""), article_data.get("content", "")
                )
            NewsArticle.objects.create(
                feed=feed,
                title=article_data["title"],
                url=article_data["url"],
                content=article_data.get("content", ""),
                summary=summary,
                image_url=article_data.get("image_url", ""),
                author=article_data.get("author", ""),
                published_at=article_data.get("published_at"),
            )
            scraped += 1
        feed.last_scraped = timezone.now()
        feed.save()
        return {"success": True, "scraped": scraped, "feed": feed.name}
    except Exception as e:
        raise HttpError(500, f"Scrape failed: {e}")


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


# ─── Notes ────────────────────────────────────────────────────────────


@router.get("/notes", response=list[NoteResponse])
def list_notes(
    request,
    format: str = Query(None),
    tag: str = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(PAGE_SIZE, ge=1, le=100),
):
    """List notes for current user."""
    qs = Note.objects.filter(user=request.auth)
    if format:
        qs = qs.filter(format=format)
    if tag:
        qs = qs.filter(tags__contains=tag)
    offset = (page - 1) * page_size
    return list(qs[offset : offset + page_size])


@router.post("/notes", response=NoteResponse)
def create_note(request, payload: NoteCreate):
    """Create a new note."""
    note = Note.objects.create(
        user=request.auth,
        **payload.dict(),
    )
    return note


@router.get("/notes/{note_id}", response=NoteResponse)
def get_note(request, note_id: str):
    """Get note by ID."""
    try:
        return Note.objects.get(id=note_id, user=request.auth)
    except Note.DoesNotExist:
        raise HttpError(404, "Note not found")


@router.put("/notes/{note_id}", response=NoteResponse)
def update_note(request, note_id: str, payload: NoteUpdate):
    """Update a note."""
    try:
        note = Note.objects.get(id=note_id, user=request.auth)
        for field, value in payload.dict(exclude_unset=True).items():
            setattr(note, field, value)
        note.save()
        return note
    except Note.DoesNotExist:
        raise HttpError(404, "Note not found")


@router.delete("/notes/{note_id}")
def delete_note(request, note_id: str):
    """Delete a note."""
    try:
        Note.objects.get(id=note_id, user=request.auth).delete()
        return {"success": True}
    except Note.DoesNotExist:
        raise HttpError(404, "Note not found")


@router.post("/notes/{note_id}/generate", response=GeneratedDocumentResponse)
def generate_from_note(request, note_id: str, payload: NoteGenerateRequest):
    """Generate a presentation/article from a note and save it as a document."""
    try:
        note = Note.objects.get(id=note_id, user=request.auth)
    except Note.DoesNotExist:
        raise HttpError(404, "Note not found")

    file_format = _file_format_for(payload.target_format)
    try:
        content = _run_generation(note, payload.target_format, payload.style, payload.max_length)
    except RuntimeError as exc:
        raise HttpError(400, str(exc))

    doc = GeneratedDocument.objects.create(
        user=request.auth,
        note=note,
        title=note.title,
        content=content,
        doc_format=payload.target_format,
        file_format=file_format,
        style=payload.style,
    )
    return doc


# ─── Generated Documents ────────────────────────────────────────────


def _file_format_for(target_format: str) -> str:
    if target_format == "presentation":
        return "pptx"
    return "docx"


def _run_generation(note: Note, target_format: str, style: str, max_length: int | None = None) -> str:
    """Generate the document content from the note via a direct LLM call.

    Deliberately bypasses the agent graph: the agent treats ``organize_notes``
    as a write tool that only gets *proposed* for confirmation, which made the
    output a confirmation prompt instead of the actual document.
    """
    from apps.workspace.services.document_generation import generate_content

    return generate_content(
        note.user,
        note.title,
        note.content,
        target_format,
        style,
        max_length,
    )


@router.get("/generated-documents", response=list[GeneratedDocumentResponse])
def list_generated_documents(request, doc_format: str = ""):
    """List the user's generated documents (presentations/articles)."""
    qs = GeneratedDocument.objects.filter(user=request.auth).select_related("note")
    if doc_format:
        qs = qs.filter(doc_format=doc_format)
    return list(qs)


@router.get("/generated-documents/{doc_id}", response=GeneratedDocumentResponse)
def get_generated_document(request, doc_id: str):
    """Get a single generated document."""
    doc = _get_doc(request, doc_id)
    return doc


@router.put("/generated-documents/{doc_id}", response=GeneratedDocumentResponse)
def update_generated_document(request, doc_id: str, payload: GeneratedDocumentUpdate):
    """Rename or restyle a generated document."""
    doc = _get_doc(request, doc_id)
    if payload.title is not None:
        doc.title = payload.title
    if payload.style is not None:
        doc.style = payload.style
    doc.save()
    return doc


@router.delete("/generated-documents/{doc_id}")
def delete_generated_document(request, doc_id: str):
    """Delete a generated document."""
    doc = _get_doc(request, doc_id)
    doc.delete()
    return {"success": True}


@router.post("/generated-documents/{doc_id}/regenerate", response=GeneratedDocumentResponse)
def regenerate_generated_document(request, doc_id: str, payload: NoteGenerateRequest):
    """Regenerate a document from its source note."""
    doc = _get_doc(request, doc_id)
    file_format = _file_format_for(payload.target_format)
    content = _run_generation(doc.note, payload.target_format, payload.style, payload.max_length)
    doc.content = content
    doc.doc_format = payload.target_format
    doc.file_format = file_format
    doc.style = payload.style
    doc.save()
    return doc


@router.get("/generated-documents/{doc_id}/download")
def download_generated_document(request, doc_id: str, format: str = ""):
    """Download a generated document as DOCX, PPTX or Markdown."""
    from django.http import HttpResponse

    from .services.document_generation import build_document_bytes, default_filename

    doc = _get_doc(request, doc_id)
    fmt = format or doc.file_format
    if fmt not in ("docx", "pptx", "md"):
        raise HttpError(400, "format must be docx, pptx or md")

    content_type = {
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "md": "text/markdown; charset=utf-8",
    }[fmt]
    data = build_document_bytes(doc.title, doc.content, fmt)
    response = HttpResponse(data, content_type=content_type)
    response["Content-Disposition"] = f'attachment; filename="{default_filename(doc.title, fmt)}"'
    return response


def _get_doc(request, doc_id: str) -> GeneratedDocument:
    try:
        return GeneratedDocument.objects.select_related("note").get(id=doc_id, user=request.auth)
    except GeneratedDocument.DoesNotExist:
        raise HttpError(404, "Generated document not found")


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
