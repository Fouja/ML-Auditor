"""
Google Calendar API client for calendar integration.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from django.conf import settings

from .base_oauth import BaseOAuthClient

logger = logging.getLogger(__name__)

CALENDAR_API_BASE = "https://www.googleapis.com/calendar/v3"


class CalendarClient(BaseOAuthClient):
    """
    Google Calendar API client for reading and creating events.
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
            logger.info(f"Refreshed Calendar token for user {self.user.id}")
            return True
        except Exception as e:
            logger.error(f"Failed to refresh Calendar token: {e}")
            return False

    def get_events(
        self,
        max_results: int = 100,
        time_min: Optional[datetime] = None,
        time_max: Optional[datetime] = None,
        calendar_id: str = "primary",
    ) -> List[Dict[str, Any]]:
        """
        Get calendar events.

        Args:
            max_results: Maximum events to return
            time_min: Start of time range
            time_max: End of time range
            calendar_id: Calendar to query

        Returns:
            List of events
        """
        params = {
            "maxResults": max_results,
            "singleEvents": True,
            "orderBy": "startTime",
        }

        if time_min:
            params["timeMin"] = time_min.isoformat() + "Z"
        if time_max:
            params["timeMax"] = time_max.isoformat() + "Z"

        response = self.get(
            f"{CALENDAR_API_BASE}/calendars/{calendar_id}/events",
            params=params,
        )
        return response.get("items", [])

    def get_event(
        self, event_id: str, calendar_id: str = "primary"
    ) -> Dict[str, Any]:
        """
        Get a specific event by ID.

        Args:
            event_id: Event ID
            calendar_id: Calendar ID

        Returns:
            Event data
        """
        return self.get(
            f"{CALENDAR_API_BASE}/calendars/{calendar_id}/events/{event_id}"
        )

    def create_event(
        self,
        summary: str,
        start_time: datetime,
        end_time: datetime,
        description: Optional[str] = None,
        location: Optional[str] = None,
        attendees: Optional[List[str]] = None,
        calendar_id: str = "primary",
    ) -> Dict[str, Any]:
        """
        Create a new calendar event.

        Args:
            summary: Event title
            start_time: Event start time
            end_time: Event end time
            description: Event description
            location: Event location
            attendees: List of attendee emails
            calendar_id: Calendar to add event to

        Returns:
            Created event data
        """
        event = {
            "summary": summary,
            "start": {
                "dateTime": start_time.isoformat(),
                "timeZone": "UTC",
            },
            "end": {
                "dateTime": end_time.isoformat(),
                "timeZone": "UTC",
            },
        }

        if description:
            event["description"] = description
        if location:
            event["location"] = location
        if attendees:
            event["attendees"] = [{"email": email} for email in attendees]

        return self.post(
            f"{CALENDAR_API_BASE}/calendars/{calendar_id}/events",
            data=event,
        )

    def update_event(
        self,
        event_id: str,
        updates: Dict[str, Any],
        calendar_id: str = "primary",
    ) -> Dict[str, Any]:
        """
        Update an existing event.

        Args:
            event_id: Event ID to update
            updates: Fields to update
            calendar_id: Calendar ID

        Returns:
            Updated event data
        """
        return self.put(
            f"{CALENDAR_API_BASE}/calendars/{calendar_id}/events/{event_id}",
            data=updates,
        )

    def delete_event(
        self, event_id: str, calendar_id: str = "primary"
    ) -> bool:
        """
        Delete an event.

        Args:
            event_id: Event ID to delete
            calendar_id: Calendar ID

        Returns:
            True if successful
        """
        try:
            self.delete(
                f"{CALENDAR_API_BASE}/calendars/{calendar_id}/events/{event_id}"
            )
            return True
        except Exception:
            return False

    def get_upcoming_events(
        self, hours: int = 24, calendar_id: str = "primary"
    ) -> List[Dict[str, Any]]:
        """
        Get events in the next N hours.

        Args:
            hours: Number of hours to look ahead
            calendar_id: Calendar ID

        Returns:
            List of upcoming events
        """
        now = datetime.utcnow()
        end = now + timedelta(hours=hours)

        return self.get_events(
            time_min=now,
            time_max=end,
            calendar_id=calendar_id,
        )
