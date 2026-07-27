"""
Kijiji scraper job for marketplace monitoring.
"""

import logging
from typing import Any, Dict

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def scrape_kijiji_messages_job(self, user_id: str):
    """
    Scrape messages from Kijiji inbox.

    Args:
        user_id: User ID
    """
    from apps.users.models import User
    from apps.users.services import KijijiScraperService

    try:
        user = User.objects.get(id=user_id)
        scraper = KijijiScraperService(user)

        # Get messages
        messages = scraper.get_messages(limit=50)

        logger.info(f"Scraped {len(messages)} Kijiji messages for user {user_id}")
        return {"status": "success", "messages_count": len(messages)}

    except User.DoesNotExist:
        logger.error(f"User {user_id} not found")
        return {"error": "User not found"}

    except Exception as exc:
        logger.error(f"Error scraping Kijiji: {exc}")
        self.retry(exc=exc, countdown=60)
        return {"error": str(exc)}


@shared_task(bind=True, max_retries=3)
def analyze_kijiji_listing_job(self, listing_id: str):
    """
    Analyze a Kijiji listing for potential deals.

    Args:
        listing_id: Kijiji listing ID
    """
    from apps.users.services import KijijiScraperService

    try:
        scraper = KijijiScraperService()
        listing = scraper.get_listing_details(listing_id)
        analysis = scraper.analyze_listing(listing)

        logger.info(f"Analyzed Kijiji listing {listing_id}")
        return {"status": "success", "analysis": analysis}

    except Exception as exc:
        logger.error(f"Error analyzing listing: {exc}")
        self.retry(exc=exc, countdown=60)
        return {"error": str(exc)}


@shared_task
def cleanup_old_streams():
    """
    Clean up old data streams (older than 30 days).
    """
    from apps.data_streams.models import DataStream

    cutoff_date = timezone.now() - timezone.timedelta(days=30)
    deleted_count = DataStream.objects.filter(
        created_at__lt=cutoff_date,
        status="completed",
    ).delete()[0]

    logger.info(f"Cleaned up {deleted_count} old data streams")
    return {"status": "success", "deleted": deleted_count}
