"""
Base OAuth client for external service integrations.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from requests import RequestException, Session

logger = logging.getLogger(__name__)


class BaseOAuthClient(ABC):
    """
    Abstract base class for OAuth clients.
    Handles token management and HTTP requests.
    """

    def __init__(self, user):
        self.user = user
        self.session = Session()
        self._setup_session()

    def _setup_session(self):
        """Setup session with default headers."""
        token = self._get_access_token()
        if token:
            self.session.headers.update(
                {
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                }
            )

    @abstractmethod
    def _get_access_token(self) -> Optional[str]:
        """Get access token for the service."""
        pass

    @abstractmethod
    def _get_token_field(self) -> str:
        """Get the model field name for the token."""
        pass

    @abstractmethod
    def refresh_token(self) -> bool:
        """Refresh the access token."""
        pass

    def _make_request(
        self,
        method: str,
        url: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Make an HTTP request with error handling.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            url: Request URL
            data: Request body data
            params: Query parameters

        Returns:
            Response data as dictionary
        """
        try:
            response = self.session.request(
                method=method,
                url=url,
                json=data,
                params=params,
                timeout=30,
            )
            response.raise_for_status()
            return response.json()
        except RequestException as e:
            logger.error(f"Request failed: {e}")
            if hasattr(e, "response") and e.response is not None:
                logger.error(f"Response: {e.response.text}")
            raise

    def get(self, url: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make a GET request."""
        return self._make_request("GET", url, params=params)

    def post(self, url: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make a POST request."""
        return self._make_request("POST", url, data=data)

    def put(self, url: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make a PUT request."""
        return self._make_request("PUT", url, data=data)

    def delete(self, url: str) -> Dict[str, Any]:
        """Make a DELETE request."""
        return self._make_request("DELETE", url)
