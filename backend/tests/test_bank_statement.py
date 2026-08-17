"""
Tests for formal bank statement PDF generation.
"""

from pathlib import Path
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.django_db


@pytest.fixture
def media_root(tmp_path, settings):
    settings.MEDIA_ROOT = str(tmp_path / "media")
    return str(settings.MEDIA_ROOT)


def _make_transactions():
    return [
        {
            "transaction_id": "txn-1",
            "date": "2026-05-01",
            "name": "ACME PAYROLL",
            "merchant_name": "ACME Inc",
            "category": ["Income", "Payroll"],
            "amount": -3000.0,
            "account_id": "acc-1",
        },
        {
            "transaction_id": "txn-2",
            "date": "2026-05-03",
            "name": "UBER",
            "category": ["Travel", "Taxi"],
            "amount": 23.45,
            "account_id": "acc-1",
        },
    ]


def _make_accounts():
    return [
        {
            "account_id": "acc-1",
            "name": "Plaid Checking",
            "official_name": "Plaid Checking",
            "type": "depository",
            "subtype": "checking",
            "mask": "1234",
            "institution_id": "ins_123",
            "balances": {"current": 4976.55, "available": 4976.55},
        }
    ]


def _mock_plaid(instance, transactions=None, accounts=None):
    instance.get_transactions.return_value = transactions or []
    instance.get_accounts.return_value = accounts or []
    instance.get_institution_by_id.return_value = {
        "institution": {"name": "First National Bank"}
    }


class TestBankStatementPdf:
    def test_generate_success(self, user, media_root):
        from apps.agents.services.bank_statement_pdf import generate_bank_statement_pdf

        user.plaid_access_token = "access-sandbox-abc"
        user.save()

        with patch("apps.users.services.PlaidClient") as mock_cls:
            _mock_plaid(
                mock_cls.return_value,
                transactions=_make_transactions(),
                accounts=_make_accounts(),
            )
            result = generate_bank_statement_pdf(user, 5, 2026)

        assert result["success"] is True
        assert result["file_url"].startswith("/media/bank_statements/")
        assert result["filename"] == "bank-statement-2026-05.pdf"
        assert result["bank"] == "First National Bank"
        assert result["transactions_count"] == 2

        file_path = Path(result["file_path"])
        assert file_path.exists()
        assert file_path.read_bytes()[:4] == b"%PDF"

        # opening = closing + withdrawn - deposited
        assert result["summary"]["opening_balance"] == 2000.0
        assert result["summary"]["total_deposited"] == 3000.0
        assert result["summary"]["total_withdrawn"] == 23.45
        assert result["summary"]["closing_balance"] == 4976.55

    def test_generate_without_plaid(self, user, media_root):
        from apps.agents.services.bank_statement_pdf import generate_bank_statement_pdf

        user.plaid_access_token = None
        user.save()

        result = generate_bank_statement_pdf(user, 5, 2026)
        assert result["success"] is False
        assert result["error"] == "Plaid not connected"

    def test_invalid_month(self, user, media_root):
        from apps.agents.services.bank_statement_pdf import generate_bank_statement_pdf

        user.plaid_access_token = "access-sandbox-abc"
        user.save()

        result = generate_bank_statement_pdf(user, 13, 2026)
        assert result["success"] is False
        assert "Month" in result["error"]

    def test_no_transactions(self, user, media_root):
        from apps.agents.services.bank_statement_pdf import generate_bank_statement_pdf

        user.plaid_access_token = "access-sandbox-abc"
        user.save()

        with patch("apps.users.services.PlaidClient") as mock_cls:
            _mock_plaid(mock_cls.return_value, transactions=[], accounts=_make_accounts())
            result = generate_bank_statement_pdf(user, 5, 2026)

        assert result["success"] is True
        assert result["transactions_count"] == 0
        assert result["summary"]["opening_balance"] == 4976.55
        assert Path(result["file_path"]).exists()

    def test_pagination(self, user, media_root):
        from apps.agents.services.bank_statement_pdf import generate_bank_statement_pdf

        user.plaid_access_token = "access-sandbox-abc"
        user.save()

        page_a = [
            {"transaction_id": f"txn-{i}", "date": "2026-05-01", "name": "Page A", "amount": -1.0}
            for i in range(500)
        ]
        page_b = [
            {"transaction_id": f"page-b-{i}", "date": "2026-05-02", "name": "Page B", "amount": -1.0}
            for i in range(3)
        ]

        with patch("apps.users.services.PlaidClient") as mock_cls:
            instance = mock_cls.return_value
            instance.get_transactions.side_effect = [page_a, page_b]
            instance.get_accounts.return_value = _make_accounts()
            instance.get_institution_by_id.return_value = {
                "institution": {"name": "First National Bank"}
            }
            result = generate_bank_statement_pdf(user, 5, 2026)

        assert result["success"] is True
        assert result["transactions_count"] == 503
        assert instance.get_transactions.call_count == 2
        assert instance.get_transactions.call_args_list[1].kwargs["offset"] == 500
        assert Path(result["file_path"]).exists()

    def test_account_filter(self, user, media_root):
        from apps.agents.services.bank_statement_pdf import generate_bank_statement_pdf

        user.plaid_access_token = "access-sandbox-abc"
        user.save()

        transactions = [
            {"transaction_id": "a", "date": "2026-05-01", "name": "A", "amount": -10.0, "account_id": "acc-1"},
            {"transaction_id": "b", "date": "2026-05-02", "name": "B", "amount": -20.0, "account_id": "acc-2"},
        ]
        accounts = _make_accounts() + [
            {
                "account_id": "acc-2",
                "name": "Plaid Credit",
                "type": "credit",
                "subtype": "credit card",
                "mask": "5678",
                "institution_id": "ins_123",
                "balances": {"current": 100.0},
            }
        ]

        with patch("apps.users.services.PlaidClient") as mock_cls:
            _mock_plaid(mock_cls.return_value, transactions=transactions, accounts=accounts)
            result = generate_bank_statement_pdf(user, 5, 2026, account_id="acc-1")

        assert result["success"] is True
        assert result["transactions_count"] == 1
        assert len(result["accounts"]) == 1
        assert result["accounts"][0]["id"] == "acc-1"
        assert Path(result["file_path"]).exists()
