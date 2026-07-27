"""
Workspace models for ML-Auditor.
Tasks, Calendar Events, News Feeds, and Widget layout.
"""

import uuid

from django.conf import settings
from django.db import models


class Task(models.Model):
    """Task model for Wall of Work / Kanban board."""

    class Status(models.TextChoices):
        TODO = "todo", "To Do"
        IN_PROGRESS = "in_progress", "In Progress"
        REVIEW = "review", "Review"
        DONE = "done", "Done"

    class Priority(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        CRITICAL = "critical", "Critical"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="workspace_tasks",
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.TODO,
    )
    priority = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.MEDIUM,
    )
    due_date = models.DateTimeField(null=True, blank=True)
    tags = models.JSONField(default=list, blank=True)
    position = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["position", "-created_at"]
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["user", "priority"]),
            models.Index(fields=["user", "due_date"]),
        ]

    def __str__(self):
        return f"[{self.status}] {self.title}"


class CalendarEvent(models.Model):
    """Calendar event model."""

    class Recurrence(models.TextChoices):
        NONE = "none", "None"
        DAILY = "daily", "Daily"
        WEEKLY = "weekly", "Weekly"
        MONTHLY = "monthly", "Monthly"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="workspace_events",
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    location = models.CharField(max_length=500, blank=True, default="")
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    all_day = models.BooleanField(default=False)
    recurrence = models.CharField(
        max_length=20,
        choices=Recurrence.choices,
        default=Recurrence.NONE,
    )
    reminder_minutes = models.IntegerField(default=30)
    color = models.CharField(max_length=7, default="#3b82f6")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["start_time"]
        indexes = [
            models.Index(fields=["user", "start_time"]),
        ]

    def __str__(self):
        return f"{self.title} - {self.start_time}"


class NewsFeed(models.Model):
    """News feed source (RSS or URL to scrape)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="workspace_feeds",
    )
    name = models.CharField(max_length=255)
    url = models.URLField()
    feed_type = models.CharField(
        max_length=20,
        choices=[
            ("rss", "RSS Feed"),
            ("webpage", "Web Page"),
        ],
        default="rss",
    )
    is_active = models.BooleanField(default=True)
    scrape_interval_minutes = models.IntegerField(default=60)
    last_scraped = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class NewsArticle(models.Model):
    """Scraped news article."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    feed = models.ForeignKey(
        NewsFeed,
        on_delete=models.CASCADE,
        related_name="articles",
    )
    title = models.CharField(max_length=500)
    url = models.URLField()
    content = models.TextField(blank=True, default="")
    summary = models.TextField(blank=True, default="")
    author = models.CharField(max_length=255, blank=True, default="")
    published_at = models.DateTimeField(null=True, blank=True)
    is_read = models.BooleanField(default=False)
    is_bookmarked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-published_at"]
        indexes = [
            models.Index(fields=["feed", "published_at"]),
            models.Index(fields=["feed", "is_read"]),
        ]

    def __str__(self):
        return self.title


class WorkspaceWidget(models.Model):
    """Widget configuration for bento grid layout."""

    class WidgetType(models.TextChoices):
        WALL_OF_WORK = "wall_of_work", "Wall of Work"
        CALENDAR = "calendar", "Calendar"
        NEWS_FEED = "news_feed", "News Feed"
        QUICK_NOTES = "quick_notes", "Quick Notes"
        STATS = "stats", "Statistics"
        RECENT_ACTIVITY = "recent_activity", "Recent Activity"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="workspace_widgets",
    )
    widget_type = models.CharField(
        max_length=30,
        choices=WidgetType.choices,
    )
    title = models.CharField(max_length=255)
    position_x = models.IntegerField(default=0)
    position_y = models.IntegerField(default=0)
    width = models.IntegerField(default=1)
    height = models.IntegerField(default=1)
    is_visible = models.BooleanField(default=True)
    config = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["position_y", "position_x"]

    def __str__(self):
        return f"{self.title} ({self.widget_type})"


class Trigger(models.Model):
    """Trigger / reminder system."""

    class TriggerType(models.TextChoices):
        TIME_BASED = "time_based", "Time Based"
        EVENT_BASED = "event_based", "Event Based"
        MANUAL = "manual", "Manual"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="workspace_triggers",
    )
    name = models.CharField(max_length=255)
    trigger_type = models.CharField(
        max_length=20,
        choices=TriggerType.choices,
        default=TriggerType.TIME_BASED,
    )
    trigger_time = models.DateTimeField(null=True, blank=True)
    trigger_minutes_before = models.IntegerField(null=True, blank=True)
    message = models.TextField()
    action_type = models.CharField(
        max_length=50,
        choices=[
            ("alert", "Create Alert"),
            ("notification", "Send Notification"),
            ("email", "Send Email"),
        ],
        default="notification",
    )
    is_active = models.BooleanField(default=True)
    last_fired = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["trigger_time"]

    def __str__(self):
        return f"{self.name} ({self.trigger_type})"
