"""
Celery tasks for Workspace.
News scraping and trigger checking.
"""

import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def scrape_news_feeds(self):
    """Periodically scrape all active news feeds."""
    from apps.workspace.models import NewsArticle, NewsFeed

    feeds = NewsFeed.objects.filter(is_active=True)
    scraped_count = 0

    for feed in feeds:
        try:
            articles = _fetch_feed(feed)
            for article_data in articles:
                if not NewsArticle.objects.filter(url=article_data["url"]).exists():
                    NewsArticle.objects.create(
                        feed=feed,
                        title=article_data["title"],
                        url=article_data["url"],
                        content=article_data.get("content", ""),
                        author=article_data.get("author", ""),
                        published_at=article_data.get("published_at"),
                    )
                    scraped_count += 1

            feed.last_scraped = timezone.now()
            feed.save()
            logger.info(f"Scraped {feed.name}: {scraped_count} new articles")

        except Exception as exc:
            logger.error(f"Error scraping {feed.name}: {exc}")
            self.retry(exc=exc, countdown=60)

    return {"scraped_count": scraped_count, "feeds_processed": feeds.count()}


def _fetch_feed(feed):
    """Fetch articles from a feed URL."""
    import httpx

    articles = []
    try:
        response = httpx.get(feed.url, timeout=30, follow_redirects=True)
        response.raise_for_status()

        # Simple HTML parsing for webpage feeds
        if feed.feed_type == "webpage":
            from html.parser import HTMLParser

            class LinkParser(HTMLParser):
                def __init__(self):
                    super().__init__()
                    self.in_a = False
                    self.current_title = ""
                    self.articles = []

                def handle_starttag(self, tag, attrs):
                    if tag == "a":
                        self.in_a = True
                        self.current_title = ""

                def handle_data(self, data):
                    if self.in_a:
                        self.current_title += data

                def handle_endtag(self, tag):
                    if tag == "a" and self.in_a:
                        self.in_a = False
                        if self.current_title.strip():
                            self.articles.append(
                                {
                                    "title": self.current_title.strip(),
                                    "url": feed.url,
                                    "content": "",
                                }
                            )

            parser = LinkParser()
            parser.feed(response.text)
            articles = parser.articles[:10]  # Limit to 10 articles

    except Exception as e:
        logger.error(f"Error fetching feed {feed.url}: {e}")

    return articles


@shared_task(bind=True)
def check_triggers(self):
    """Check and fire active triggers."""
    from apps.alerts.models import AgentAlert
    from apps.workspace.models import CalendarEvent, Trigger

    now = timezone.now()
    fired_count = 0

    # Check time-based triggers
    triggers = Trigger.objects.filter(
        is_active=True,
        trigger_type="time_based",
        trigger_time__lte=now,
        last_fired__isnull=True,
    )

    for trigger in triggers:
        try:
            # Create alert
            AgentAlert.objects.create(
                user=trigger.user,
                title=trigger.name,
                description=trigger.message,
                severity="medium",
                source_type="trigger",
                source_id=str(trigger.id),
            )
            trigger.last_fired = now
            trigger.save()
            fired_count += 1
            logger.info(f"Fired trigger: {trigger.name}")
        except Exception as exc:
            logger.error(f"Error firing trigger {trigger.name}: {exc}")

    # Check calendar event reminders
    upcoming = CalendarEvent.objects.filter(
        start_time__gte=now,
        start_time__lte=now + timezone.timedelta(hours=1),
    )

    for event in upcoming:
        reminder_time = event.start_time - timezone.timedelta(
            minutes=event.reminder_minutes
        )
        if reminder_time <= now:
            # Check if reminder already sent
            existing = AgentAlert.objects.filter(
                user=event.user,
                source_type="event_reminder",
                source_id=str(event.id),
            ).exists()

            if not existing:
                AgentAlert.objects.create(
                    user=event.user,
                    title=f"Rappel: {event.title}",
                    description=f"Dans {event.reminder_minutes} minutes - {event.location or 'Pas de lieu'}",
                    severity="high",
                    source_type="event_reminder",
                    source_id=str(event.id),
                )
                fired_count += 1

    return {"fired_count": fired_count}
