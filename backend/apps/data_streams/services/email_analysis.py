"""
Email analysis job for processing incoming emails.
"""

import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def analyze_email_job(self, stream_id: str):
    """
    Analyze an incoming email from Gmail.

    Args:
        stream_id: DataStream ID containing email data
    """
    from apps.data_streams.models import DataStream
    from apps.users.services import GmailClient

    try:
        stream = DataStream.objects.get(id=stream_id)
        user = stream.user

        # Get email data from payload
        email_data = stream.payload
        message_id = email_data.get("message_id")

        if not message_id:
            logger.error(f"No message_id in stream {stream_id}")
            return {"error": "No message_id"}

        # Fetch full email from Gmail
        gmail = GmailClient(user)
        message = gmail.get_message(message_id)

        # Extract relevant data
        subject = ""
        sender = ""
        body = ""

        headers = message.get("payload", {}).get("headers", [])
        for header in headers:
            if header.get("name") == "Subject":
                subject = header.get("value", "")
            elif header.get("name") == "From":
                sender = header.get("value", "")

        body = gmail.get_message_body(message_id)

        # Update stream with processed data
        stream.payload.update(
            {
                "subject": subject,
                "sender": sender,
                "body_preview": body[:500] if body else "",
                "processed_at": timezone.now().isoformat(),
            }
        )
        stream.status = "completed"
        stream.processed_at = timezone.now()
        stream.save()

        # TODO: Create document chunk for RAG
        # TODO: Create alert if important
        # TODO: Classify email category

        logger.info(f"Email analyzed for stream {stream_id}")
        return {"status": "success", "stream_id": stream_id}

    except DataStream.DoesNotExist:
        logger.error(f"Stream {stream_id} not found")
        return {"error": "Stream not found"}

    except Exception as exc:
        logger.error(f"Error analyzing email: {exc}")
        self.retry(exc=exc, countdown=60)
        return {"error": str(exc)}
