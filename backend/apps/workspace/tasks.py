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
                    scraped_count += 1

            feed.last_scraped = timezone.now()
            feed.save()
            logger.info(f"Scraped {feed.name}: {scraped_count} new articles")

        except Exception as exc:
            logger.error(f"Error scraping {feed.name}: {exc}")
            self.retry(exc=exc, countdown=60)

    return {"scraped_count": scraped_count, "feeds_processed": feeds.count()}


def _fetch_feed(feed):
    """Fetch articles from a feed URL (RSS/Atom or web page) via the web-tools
    microservice, falling back to direct parsing when it is unreachable."""
    if feed.feed_type == "rss":
        return _fetch_rss(feed.url)
    return _fetch_webpage_feed(feed)


def _fetch_rss(url):
    import asyncio
    import feedparser

    entries = feedparser.parse(url).entries
    if not entries:
        # try the web-tools microservice parser as fallback
        from apps.agents.services import web_tools_client

        try:
            entries = asyncio.run(web_tools_client.parse_rss(url))
        except Exception as e:
            logger.warning(f"RSS fallback parse failed for {url}: {e}")
            return []
        return [_normalize_rss_entry(e) for e in entries if e.get("link")]

    articles = []
    for e in entries[:20]:
        link = e.get("link")
        if not link:
            continue
        articles.append(
            {
                "title": (e.get("title") or "").strip(),
                "url": link,
                "content": (e.get("content", [{}])[0].get("value") or "")[:3000]
                if e.get("content")
                else (e.get("summary") or ""),
                "summary": (e.get("summary") or "")[:500],
                "author": e.get("author") or "",
                "published_at": _rss_date(e),
                "image_url": _rss_image(e),
            }
        )
    return articles


def _normalize_rss_entry(e):
    return {
        "title": (e.get("title") or "").strip(),
        "url": e.get("link") or "",
        "content": (e.get("content") or "")[:3000],
        "summary": (e.get("summary") or "")[:500],
        "author": e.get("author") or "",
        "published_at": e.get("published_at") or None,
        "image_url": e.get("image_url") or "",
    }


def _rss_date(e):
    import time

    if e.get("published_parsed"):
        return time.strftime("%Y-%m-%dT%H:%M:%SZ", e["published_parsed"])
    return None


def _rss_image(e):
    for link in e.get("links", []):
        if link.get("rel") in ("enclosure", "thumbnail") and link.get("type", "").startswith("image"):
            return link.get("href", "")
    if e.get("media_content"):
        return e["media_content"][0].get("url", "")
    if e.get("media_thumbnail"):
        return e["media_thumbnail"][0].get("url", "")
    import re

    m = re.search(r'<img[^>]+src=["\']([^"\']+)', e.get("summary", "") or "")
    return m.group(1) if m else ""


def _fetch_webpage_feed(feed):
    """Read a web page (X/LinkedIn/blog/etc.) via the web-tools microservice and
    turn it into a single article entry for the feed URL."""
    import asyncio

    from apps.agents.services import web_tools_client

    try:
        scraped = asyncio.run(web_tools_client.scrape_page(feed.url))
    except Exception as e:
        logger.warning(f"webpage scrape via microservice failed for {feed.url}: {e}")
        scraped = {}

    if scraped.get("error") or not (scraped.get("content") or scraped.get("title")):
        return _fetch_webpage_feed_direct(feed)

    return [
        {
            "title": scraped.get("title") or feed.name,
            "url": feed.url,
            "content": scraped.get("content", ""),
            "summary": scraped.get("summary", ""),
            "author": scraped.get("author", ""),
            "published_at": scraped.get("published_at") or None,
            "image_url": scraped.get("image_url", ""),
        }
    ]


def _fetch_webpage_feed_direct(feed):
    """Direct httpx + BeautifulSoup fallback (no microservice)."""
    import httpx
    from bs4 import BeautifulSoup

    try:
        resp = httpx.get(feed.url, timeout=30, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        title = (soup.find("meta", property="og:title") or {}).get("content") or (
            soup.title.get_text().strip() if soup.title else feed.name
        )
        og_image = (soup.find("meta", property="og:image") or {}).get("content", "")
        paragraphs = soup.find_all("p")
        text = "\n".join(p.get_text(strip=True) for p in paragraphs[:20])
        return [
            {
                "title": title[:500],
                "url": feed.url,
                "content": text[:3000],
                "summary": "",
                "author": "",
                "published_at": None,
                "image_url": og_image or "",
            }
        ]
    except Exception as e:
        logger.error(f"Direct webpage fetch failed for {feed.url}: {e}")
        return []


def _summarize_with_llm(title, content, max_chars: int = 400) -> str:
    """Generate a concise 2-3 sentence summary with the NIM LLM."""
    import json

    from django.conf import settings

    base_url = getattr(settings, "NIM_BASE_URL", "https://integrate.api.nvidia.com/v1")
    api_key = getattr(settings, "NIM_API_KEY", "")
    model = getattr(settings, "NIM_MODEL", "meta/llama-3.1-8b-instruct")
    if not api_key:
        return ""
    text = (title + "\n" + content)[:3500]
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You summarize news articles in 2-3 concise sentences. "
                    "Respond with only the summary, in the language of the article."
                ),
            },
            {"role": "user", "content": text},
        ],
        "max_tokens": 200,
        "temperature": 0.3,
    }
    try:
        import httpx

        resp = httpx.post(
            f"{base_url}/chat/completions",
            json=payload,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=60,
        )
        resp.raise_for_status()
        summary = resp.json()["choices"][0]["message"]["content"].strip()
        return summary[:max_chars]
    except Exception as e:
        logger.warning(f"LLM summarization failed: {e}")
        return ""


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
