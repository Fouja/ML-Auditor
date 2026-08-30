"""
Plaid API client for financial data integration.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from django.conf import settings

from .base_oauth import BaseOAuthClient

logger = logging.getLogger(__name__)

PLAID_ENV_URLS = {
    "sandbox": "https://sandbox.plaid.com",
    "development": "https://development.plaid.com",
    "production": "https://production.plaid.com",
}


class PlaidClient(BaseOAuthClient):
    """
    Plaid API client for accessing bank accounts and transactions.

    Supports both the legacy single-token-per-user mode (reading from
    ``user.plaid_access_token``) and the new multi-account mode via an
    ``IntegrationConnection`` instance.
    """

    def __init__(self, user=None, connection=None):
        self.connection = connection
        super().__init__(user)
        self.env = getattr(settings, "PLAID_ENV", "sandbox")
        self.base_url = PLAID_ENV_URLS.get(self.env, PLAID_ENV_URLS["sandbox"])
        self.client_id = getattr(settings, "PLAID_CLIENT_ID", "")
        self.secret = getattr(settings, "PLAID_SECRET", "")

    @classmethod
    def with_credentials(cls, client_id: str, secret: str, environment: str = "sandbox"):
        """Create a standalone client for credential validation (no user)."""
        client = cls.__new__(cls)
        client.connection = None
        client.user = None
        client.env = environment
        client.base_url = PLAID_ENV_URLS.get(environment, PLAID_ENV_URLS["sandbox"])
        client.client_id = client_id
        client.secret = secret
        client.session = cls._new_session()
        return client

    @classmethod
    def _new_session(cls):
        import requests

        return requests.Session()

    def health_check(self) -> bool:
        """Return True if the configured Plaid credentials are valid."""
        try:
            self._make_request("POST", "/institutions/get", {"count": 1, "offset": 0, "country_codes": ["US", "CA"]})
            return True
        except Exception:
            return False

    def _get_access_token(self) -> Optional[str]:
        if self.connection:
            return self.connection.access_token
        return self.user.plaid_access_token

    def _get_token_field(self) -> str:
        return "plaid_access_token"

    def refresh_token(self) -> bool:
        """Refresh Plaid token (Plaid tokens don't expire but can be invalidated)."""
        logger.info(f"Checking Plaid token for user {self.user.id}")
        return True

    def _make_request(
        self, method: str, endpoint: str, data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Make a request to Plaid API.

        Args:
            method: HTTP method
            endpoint: API endpoint
            data: Request data

        Returns:
            Response data
        """
        url = f"{self.base_url}{endpoint}"
        request_data = {
            "client_id": self.client_id,
            "secret": self.secret,
            **(data or {}),
        }

        try:
            response = self.session.post(url, json=request_data, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Plaid API error: {e}")
            raise

    def get_accounts(self, access_token: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get all accounts for an access token.

        Args:
            access_token: Plaid access token

        Returns:
            List of accounts
        """
        token = access_token or self._get_access_token()
        response = self._make_request(
            "POST",
            "/accounts/get",
            {"access_token": token},
        )
        accounts = response.get("accounts", [])
        # Normalize field names for frontend compatibility
        for acc in accounts:
            acc["id"] = acc.get("account_id", "")
        return accounts

    def get_transactions(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        access_token: Optional[str] = None,
        count: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Get transactions for date range.

        Args:
            start_date: Start date
            end_date: End date
            access_token: Plaid access token
            count: Number of transactions per page
            offset: Pagination offset

        Returns:
            List of transactions
        """
        token = access_token or self._get_access_token()

        if not start_date:
            start_date = datetime.now() - timedelta(days=30)
        if not end_date:
            end_date = datetime.now()

        response = self._make_request(
            "POST",
            "/transactions/get",
            {
                "access_token": token,
                "start_date": start_date.strftime("%Y-%m-%d"),
                "end_date": end_date.strftime("%Y-%m-%d"),
                "options": {"count": count, "offset": offset},
            },
        )
        transactions = response.get("transactions", [])
        # Normalize field names for frontend compatibility
        for tx in transactions:
            tx["id"] = tx.get("transaction_id", "")
        return transactions

    def get_balances(self, access_token: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get current balances for all accounts.

        Args:
            access_token: Plaid access token

        Returns:
            List of account balances
        """
        accounts = self.get_accounts(access_token)
        return [
            {
                "id": acc.get("account_id", ""),
                "account_id": acc.get("account_id"),
                "name": acc.get("name"),
                "type": acc.get("type"),
                "subtype": acc.get("subtype"),
                "balances": acc.get("balances", {}),
            }
            for acc in accounts
        ]

    def create_link_token(
        self,
        user_id: str,
        products: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Create a link token for Plaid Link.

        Args:
            user_id: User identifier
            products: Plaid products to request

        Returns:
            Link token data
        """
        if not products:
            products = ["transactions"]

        return self._make_request(
            "POST",
            "/link/token/create",
            {
                "user": {"client_user_id": user_id},
                "client_name": "ML-Auditor",
                "products": products,
                "country_codes": ["CA", "US"],
                "language": "en",
            },
        )

    def exchange_public_token(self, public_token: str) -> Dict[str, Any]:
        """
        Exchange public token for access token.

        Args:
            public_token: Public token from Plaid Link

        Returns:
            Access token data
        """
        return self._make_request(
            "POST",
            "/item/public_token/exchange",
            {"public_token": public_token},
        )

    def get_institutions(self, count: int = 100) -> List[Dict[str, Any]]:
        """
        Get available institutions.

        Args:
            count: Number of institutions

        Returns:
            List of institutions
        """
        response = self._make_request(
            "POST",
            "/institutions/get",
            {"count": count, "country_codes": ["CA", "US"]},
        )
        return response.get("institutions", [])

    def get_institution_by_id(self, institution_id: str) -> Dict[str, Any]:
        """
        Get institution details (name, url, logo, address) by ID.

        Args:
            institution_id: Plaid institution ID

        Returns:
            Institution data
        """
        return self._make_request(
            "POST",
            "/institutions/get_by_id",
            {
                "institution_id": institution_id,
                "country_codes": ["CA", "US"],
                "options": {"include_optional_metadata": True},
            },
        )
