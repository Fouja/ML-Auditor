"""
Gmail API client for email integration.
"""

import logging
from typing import Any, Dict, List, Optional

from django.conf import settings

from .base_oauth import BaseOAuthClient

logger = logging.getLogger(__name__)

GMAIL_API_BASE = "https://gmail.googleapis.com/gmail/v1/users/me"


class GmailClient(BaseOAuthClient):
    """
    Gmail API client for reading and sending emails.
    """

    def _get_access_token(self) -> Optional[str]:
        return self.user.google_access_token

    def _get_token_field(self) -> str:
        return "google_access_token"

    def refresh_token(self) -> bool:
        """Refresh Google OAuth token using refresh_token."""
        from requests import post as requests_post

        if not self.user.google_refresh_token:
            logger.warning(f"No refresh token for user {self.user.id}")
            return False

        try:
            resp = requests_post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
                    "client_secret": settings.GOOGLE_OAUTH_CLIENT_SECRET,
                    "refresh_token": self.user.google_refresh_token,
                    "grant_type": "refresh_token",
                },
                timeout=10,
            )
            resp.raise_for_status()
            token_data = resp.json()
            self.user.google_access_token = token_data["access_token"]
            self.user.save(update_fields=["google_access_token"])
            self._setup_session()
            logger.info(f"Refreshed Gmail token for user {self.user.id}")
            return True
        except Exception as e:
            logger.error(f"Failed to refresh Gmail token: {e}")
            return False

    def get_messages(
        self,
        max_results: int = 100,
        query: Optional[str] = None,
        label_ids: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get list of messages from Gmail.

        Args:
            max_results: Maximum number of messages to return
            query: Search query (Gmail syntax)
            label_ids: Filter by label IDs

        Returns:
            List of message metadata
        """
        params = {"maxResults": max_results}
        if query:
            params["q"] = query
        if label_ids:
            params["labelIds"] = label_ids

        response = self.get(f"{GMAIL_API_BASE}/messages", params=params)
        return response.get("messages", [])

    def get_message(self, message_id: str) -> Dict[str, Any]:
        """
        Get full message by ID.

        Args:
            message_id: Gmail message ID

        Returns:
            Full message data
        """
        return self.get(f"{GMAIL_API_BASE}/messages/{message_id}")

    def get_message_body(self, message_id: str) -> str:
        """
        Extract message body text.

        Args:
            message_id: Gmail message ID

        Returns:
            Message body as text
        """
        message = self.get_message(message_id)
        payload = message.get("payload", {})
        parts = payload.get("parts", [])

        if not parts:
            # Simple message
            body_data = payload.get("body", {}).get("data", "")
            if body_data:
                import base64

                return base64.urlsafe_b64decode(body_data).decode("utf-8")
            return ""

        # Multipart message
        body_parts = []
        for part in parts:
            if part.get("mimeType") == "text/plain":
                body_data = part.get("body", {}).get("data", "")
                if body_data:
                    import base64

                    body_parts.append(
                        base64.urlsafe_b64decode(body_data).decode("utf-8")
                    )

        return "\n".join(body_parts)

    def send_message(
        self,
        to: str,
        subject: str,
        body: str,
        cc: Optional[str] = None,
        bcc: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send an email via Gmail.

        Args:
            to: Recipient email
            subject: Email subject
            body: Email body
            cc: CC recipients
            bcc: BCC recipients

        Returns:
            Sent message data
        """
        import base64
        from email.mime.text import MIMEText

        message = MIMEText(body)
        message["to"] = to
        message["subject"] = subject
        if cc:
            message["cc"] = cc
        if bcc:
            message["bcc"] = bcc

        raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
        return self.post(
            f"{GMAIL_API_BASE}/messages/send",
            data={"raw": raw},
        )

    def get_labels(self) -> List[Dict[str, Any]]:
        """Get all labels for the user."""
        response = self.get(f"{GMAIL_API_BASE}/labels")
        return response.get("labels", [])

    def get_unread_count(self) -> int:
        """Get count of unread messages."""
        response = self.get(
            f"{GMAIL_API_BASE}/messages",
            params={"q": "is:unread", "maxResults": 1},
        )
        return response.get("resultSizeEstimate", 0)
