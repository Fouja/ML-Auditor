"""
Formal bank statement PDF generation.

Builds a letterhead-style statement (bank logo, bank name and address,
account holder info, statement period, balance summary and an itemised
transaction table) from Plaid data. Output is suitable for sharing with
institutions and government bodies.

Bank branding can be configured through Django settings:

    BANK_STATEMENT_BRANDING = {
        "bank_name": "First National Bank",
        "logo_path": "/app/static/bank/logo.png",
        "address_lines": ["Head Office", "1 Financial Plaza", "Toronto, ON", "Canada"],
        "phone": "(800) 555-0199",
        "website": "www.firstnational.example",
        "email": "support@firstnational.example",
    }

When no logo file is configured, a clean monogram logo is drawn in code.
"""

import calendar
import logging
from datetime import date, datetime
from pathlib import Path
from typing import Optional
from xml.sax.saxutils import escape

from django.conf import settings
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

logger = logging.getLogger(__name__)

MONTH_NAMES = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
]

BRANDING_DEFAULTS = {
    "bank_name": "ML-Auditor Financial Services",
    "logo_path": "",
    "address_lines": [
        "Head Office",
        "1 Financial Plaza",
        "Toronto, ON M5H 2Y4",
        "Canada",
    ],
    "phone": "(800) 555-0199",
    "website": "www.mlauditor.example",
    "email": "support@mlauditor.example",
}

PRIMARY = colors.HexColor("#0f2557")
ACCENT = colors.HexColor("#c9a227")
MUTED = colors.HexColor("#555555")
ROW_ALT = colors.HexColor("#f4f6fb")


def _fmt_amount(value) -> str:
    try:
        return f"{float(value):,.2f}"
    except (TypeError, ValueError):
        return "0.00"


def _mask(account) -> str:
    mask = account.get("mask") or account.get("account_id", "")[-4:] or "0000"
    return f"•••• {mask}"


def _transaction_date(tx) -> str:
    return str(tx.get("date", tx.get("authorized_date", "")))


def _merchant_name(tx) -> str:
    return str(tx.get("merchant_name") or tx.get("name") or "Unknown")


def _category(tx) -> str:
    cats = tx.get("category") or []
    return ", ".join(str(c) for c in cats) if cats else "—"


def _styles():
    title = ParagraphStyle(
        name="StmtTitle",
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=PRIMARY,
        alignment=TA_LEFT,
    )
    subtitle = ParagraphStyle(
        name="StmtSubtitle",
        fontName="Helvetica",
        fontSize=10,
        leading=13,
        textColor=MUTED,
    )
    heading = ParagraphStyle(
        name="StmtHeading",
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=15,
        textColor=PRIMARY,
        spaceBefore=10,
        spaceAfter=4,
    )
    label = ParagraphStyle(
        name="StmtLabel",
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=12,
        textColor=MUTED,
    )
    value = ParagraphStyle(
        name="StmtValue",
        fontName="Helvetica",
        fontSize=10,
        leading=13,
    )
    cell = ParagraphStyle(
        name="StmtCell",
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
    )
    cell_bold = ParagraphStyle(
        name="StmtCellBold",
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=11,
    )
    cell_right = ParagraphStyle(
        name="StmtCellRight",
        parent=cell,
        alignment=TA_RIGHT,
    )
    cell_right_bold = ParagraphStyle(
        name="StmtCellRightBold",
        parent=cell_bold,
        alignment=TA_RIGHT,
    )
    footer = ParagraphStyle(
        name="StmtFooter",
        fontName="Helvetica",
        fontSize=7.5,
        leading=10,
        textColor=MUTED,
        alignment=TA_CENTER,
    )
    return {
        "title": title,
        "subtitle": subtitle,
        "heading": heading,
        "label": label,
        "value": value,
        "cell": cell,
        "cell_bold": cell_bold,
        "cell_right": cell_right,
        "cell_right_bold": cell_right_bold,
        "footer": footer,
    }


def _logo_flowable(branding: dict):
    """Return a logo flowable: the configured image, or a drawn monogram."""
    from reportlab.graphics.shapes import Drawing, Rect, String

    logo_path = branding.get("logo_path", "")
    if logo_path and Path(logo_path).exists():
        return Image(logo_path, width=16 * mm, height=16 * mm)

    bank_name = branding.get("bank_name", "ML-Auditor")
    initials = "".join(word[0] for word in bank_name.split()[:2]).upper()[:2] or "ML"

    drawing = Drawing(16 * mm, 16 * mm)
    drawing.add(
        Rect(0, 0, 16 * mm, 16 * mm, rx=2.5 * mm, ry=2.5 * mm, fillColor=PRIMARY)
    )
    drawing.add(
        Rect(
            0.8 * mm,
            0.8 * mm,
            16 * mm - 1.6 * mm,
            16 * mm - 1.6 * mm,
            rx=2.2 * mm,
            ry=2.2 * mm,
            strokeColor=ACCENT,
            strokeWidth=1,
        )
    )
    drawing.add(
        String(
            8 * mm,
            8 * mm,
            initials,
            fontName="Helvetica-Bold",
            fontSize=16,
            fillColor=colors.white,
            textAnchor="middle",
        )
    )
    return drawing


def _footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#cccccc"))
    canvas.setLineWidth(0.5)
    canvas.line(18 * mm, 12 * mm, A4[0] - 18 * mm, 12 * mm)
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(MUTED)
    canvas.drawString(18 * mm, 9 * mm, f"Page {doc.page}")
    canvas.restoreState()


def _format_period(start: date, end: date) -> str:
    start_str = f"{MONTH_NAMES[start.month - 1]} {start.day}, {start.year}"
    end_str = f"{MONTH_NAMES[end.month - 1]} {end.day}, {end.year}"
    if start.month == end.month and start.year == end.year:
        return f"{MONTH_NAMES[start.month - 1]} {start.year}"
    return f"{start_str} - {end_str}"


def _fetch_accounts_and_transactions(plaid, start: datetime, end: datetime):
    accounts = plaid.get_accounts()

    transactions = []
    offset = 0
    page_size = 500
    while True:
        page = plaid.get_transactions(
            start_date=start, end_date=end, count=page_size, offset=offset
        )
        if not page:
            break
        transactions.extend(page)
        if len(page) < page_size:
            break
        offset += page_size
        if offset >= 5000:
            break
    return accounts, transactions


def _institution_name(plaid, accounts) -> Optional[str]:
    for account in accounts:
        inst_id = account.get("institution_id")
        if not inst_id:
            continue
        try:
            resp = plaid.get_institution_by_id(inst_id)
            name = resp.get("institution", {}).get("name")
            if name:
                return name
        except Exception as e:
            logger.warning(f"Could not resolve institution name: {e}")
            continue
    return None


def _compute_balances(transactions, closing_balance: float):
    """Compute opening balance and per-transaction running balance.

    Plaid amounts are positive for money out and negative for money in.
    """
    ordered = sorted(
        transactions,
        key=lambda t: (_transaction_date(t), t.get("transaction_id", "")),
    )
    total_deposited = sum(
        abs(t.get("amount", 0)) for t in ordered if t.get("amount", 0) < 0
    )
    total_withdrawn = sum(
        t.get("amount", 0) for t in ordered if t.get("amount", 0) > 0
    )
    opening = closing_balance + total_withdrawn - total_deposited

    running = opening
    for tx in ordered:
        amount = tx.get("amount", 0) or 0
        running = running - amount
        tx["_balance"] = running
    return ordered, opening, total_deposited, total_withdrawn, closing_balance


def generate_bank_statement_pdf(user, month, year, account_id=None) -> dict:
    """Generate a formal PDF bank statement for the given month/year.

    Args:
        user: The requesting User (must have a Plaid access token).
        month: Month number (1-12).
        year: Year (e.g. 2026).
        account_id: Optional Plaid account id to restrict the statement.

    Returns:
        {"success": True, "file_path": ..., "file_url": ..., ...} on success,
        or {"success": False, "error": ...}.
    """
    if not getattr(user, "plaid_access_token", None):
        return {"success": False, "error": "Plaid not connected"}

    try:
        month = int(month)
        year = int(year)
    except (TypeError, ValueError):
        return {"success": False, "error": "Invalid month or year"}
    if month < 1 or month > 12:
        return {"success": False, "error": "Month must be between 1 and 12"}
    if year < 1900 or year > 2100:
        return {"success": False, "error": "Invalid year"}

    from apps.users.services import PlaidClient

    plaid = PlaidClient(user)
    start_dt = datetime(year, month, 1)
    last_day = calendar.monthrange(year, month)[1]
    end_dt = datetime(year, month, last_day, 23, 59, 59)

    try:
        accounts, transactions = _fetch_accounts_and_transactions(
            plaid, start_dt, end_dt
        )
    except Exception as e:
        logger.error(f"Plaid fetch failed for statement: {e}")
        return {"success": False, "error": str(e)}

    if account_id:
        accounts = [a for a in accounts if a.get("account_id") == account_id]
        transactions = [t for t in transactions if t.get("account_id") == account_id]

    closing_balance = 0.0
    if accounts:
        closing_balance = sum(
            float(a.get("balances", {}).get("current") or 0) for a in accounts
        )

    ordered, opening, total_deposited, total_withdrawn, closing = _compute_balances(
        transactions, closing_balance
    )

    branding = {**BRANDING_DEFAULTS, **(getattr(settings, "BANK_STATEMENT_BRANDING", {}) or {})}
    try:
        inst_name = _institution_name(plaid, accounts)
    except Exception:
        inst_name = None
    if inst_name:
        branding["bank_name"] = inst_name

    media_root = Path(getattr(settings, "MEDIA_ROOT", "media"))
    relative_dir = f"bank_statements/{user.id}"
    output_dir = media_root / relative_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = f"bank-statement-{year}-{month:02d}.pdf"
    file_path = output_dir / filename

    styles = _styles()
    holder_name = (user.get_full_name() or user.username or user.email or "Account Holder")

    # ─── Statement pages ─────────────────────────────────────────────
    story = []
    story.append(Spacer(1, 6 * mm))

    # Letterhead
    branding_text = [
        f"<b>{escape(branding['bank_name'])}</b>",
        *[escape(line) for line in branding.get("address_lines", [])],
        f"{escape(branding.get('phone', ''))}  |  {escape(branding.get('website', ''))}",
    ]
    head_table = Table(
        [
            [
                _logo_flowable(branding),
                Paragraph(
                    "<br/>".join(branding_text),
                    ParagraphStyle(
                        name="Branding",
                        parent=styles["subtitle"],
                        fontName="Helvetica",
                        leading=12,
                        textColor=PRIMARY,
                    ),
                ),
            ]
        ],
        colWidths=[20 * mm, 130 * mm],
    )
    head_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    story.append(head_table)

    # Double rule under letterhead
    rule = Table([[""]], colWidths=[150 * mm])
    rule.setStyle(
        TableStyle(
            [
                ("LINEABOVE", (0, 0), (-1, 0), 2, PRIMARY),
                ("LINEBELOW", (0, 0), (-1, 0), 0.6, ACCENT),
                ("TOPPADDING", (0, 0), (-1, 0), 4),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 4),
            ]
        )
    )
    story.append(rule)

    story.append(Paragraph("BANK STATEMENT", styles["title"]))
    story.append(Paragraph(
        f"Statement period: {_format_period(date(year, month, 1), date(year, month, last_day))}",
        styles["subtitle"],
    ))
    story.append(Spacer(1, 4 * mm))

    # Account holder info
    account_lines = []
    for acc in accounts:
        acc_label = (
            f"{escape(acc.get('name') or acc.get('official_name') or 'Account')} "
            f"({escape(_mask(acc))})"
        )
        account_lines.append(acc_label)
    if not account_lines:
        account_lines.append("No connected accounts")

    info_table = Table(
        [
            [
                Paragraph("ACCOUNT HOLDER", styles["label"]),
                Paragraph("ACCOUNT", styles["label"]),
            ],
            [
                Paragraph(escape(holder_name), styles["value"]),
                Paragraph("<br/>".join(account_lines), styles["value"]),
            ],
        ],
        colWidths=[75 * mm, 75 * mm],
    )
    info_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 1),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
            ]
        )
    )
    story.append(info_table)
    story.append(Spacer(1, 3 * mm))

    # Summary
    story.append(Paragraph("SUMMARY", styles["heading"]))
    summary_rows = [
        [
            Paragraph("Opening balance", styles["cell"]),
            Paragraph("", styles["cell"]),
            Paragraph("", styles["cell"]),
            Paragraph(f"$ {_fmt_amount(opening)}", styles["cell_right_bold"]),
        ],
        [
            Paragraph("Total deposits (money in)", styles["cell"]),
            Paragraph("", styles["cell"]),
            Paragraph("", styles["cell"]),
            Paragraph(f"$ {_fmt_amount(total_deposited)}", styles["cell_right"]),
        ],
        [
            Paragraph("Total withdrawals (money out)", styles["cell"]),
            Paragraph("", styles["cell"]),
            Paragraph("", styles["cell"]),
            Paragraph(f"$ {_fmt_amount(total_withdrawn)}", styles["cell_right"]),
        ],
        [
            Paragraph("Closing balance", styles["cell_bold"]),
            Paragraph("", styles["cell"]),
            Paragraph("", styles["cell"]),
            Paragraph(f"$ {_fmt_amount(closing)}", styles["cell_right_bold"]),
        ],
    ]
    summary_table = Table(summary_rows, colWidths=[60 * mm, 30 * mm, 30 * mm, 30 * mm])
    summary_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), ROW_ALT),
                ("LINEBELOW", (0, 0), (-1, -2), 0.4, colors.HexColor("#dddddd")),
                ("LINEABOVE", (0, -1), (-1, -1), 1, PRIMARY),
                ("ROWBACKGROUNDS", (1, 0), (-1, -2), [colors.white, ROW_ALT]),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    story.append(summary_table)
    story.append(Spacer(1, 3 * mm))

    # Transactions
    story.append(Paragraph("TRANSACTIONS", styles["heading"]))
    if not ordered:
        story.append(
            Paragraph(
                "No transactions were recorded during this statement period.",
                styles["value"],
            )
        )
    else:
        tx_rows = [
            [
                Paragraph("DATE", styles["cell_bold"]),
                Paragraph("DESCRIPTION", styles["cell_bold"]),
                Paragraph("CATEGORY", styles["cell_bold"]),
                Paragraph("AMOUNT ($)", styles["cell_right_bold"]),
                Paragraph("BALANCE ($)", styles["cell_right_bold"]),
            ]
        ]
        for tx in ordered:
            tx_rows.append(
                [
                    Paragraph(escape(_transaction_date(tx)), styles["cell"]),
                    Paragraph(escape(_merchant_name(tx)), styles["cell"]),
                    Paragraph(escape(_category(tx)), styles["cell"]),
                    Paragraph(
                        f"$ {_fmt_amount(tx.get('amount', 0))}", styles["cell_right"]
                    ),
                    Paragraph(
                        f"$ {_fmt_amount(tx.get('_balance', 0))}",
                        styles["cell_right"],
                    ),
                ]
            )
        tx_table = Table(
            tx_rows,
            colWidths=[24 * mm, 48 * mm, 42 * mm, 20 * mm, 22 * mm],
            repeatRows=1,
        )
        tx_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.HexColor("#cccccc")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, ROW_ALT]),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ]
            )
        )
        story.append(tx_table)

    story.append(Spacer(1, 6 * mm))

    # Statement footer note
    reference = (
        f"{year}{month:02d}-{str(user.id)[:8].upper()}"
    )
    story.append(
        Paragraph(
            "This is a computer-generated bank statement prepared by ML-Auditor from "
            f"transaction records provided by the account holder. Reference: {reference}. "
            "This document is for informational purposes and may require authentication "
            "when submitted to government or financial institutions.",
            styles["footer"],
        )
    )
    story.append(
        Paragraph(
            f"{escape(branding['bank_name'])}  |  "
            f"{escape(' | '.join(branding.get('address_lines', [])))}  |  "
            f"{escape(branding.get('phone', ''))}",
            styles["footer"],
        )
    )

    doc = SimpleDocTemplate(
        str(file_path),
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=14 * mm,
        bottomMargin=18 * mm,
        title=f"Bank Statement {_format_period(date(year, month, 1), date(year, month, last_day))}",
        author=branding["bank_name"],
        subject="Bank statement",
    )
    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)

    media_url = str(getattr(settings, "MEDIA_URL", "media/"))
    file_url = f"{media_url.rstrip('/')}/{relative_dir}/{filename}"

    return {
        "success": True,
        "file_path": str(file_path),
        "file_url": file_url,
        "filename": filename,
        "period": {
            "month": month,
            "year": year,
            "start": str(date(year, month, 1)),
            "end": str(date(year, month, last_day)),
        },
        "bank": branding["bank_name"],
        "account_holder": holder_name,
        "transactions_count": len(ordered),
        "accounts": [
            {
                "id": a.get("account_id"),
                "name": a.get("name"),
                "mask": _mask(a),
                "type": a.get("type"),
                "subtype": a.get("subtype"),
                "closing_balance": a.get("balances", {}).get("current"),
            }
            for a in accounts
        ],
        "summary": {
            "opening_balance": round(opening, 2),
            "total_deposited": round(total_deposited, 2),
            "total_withdrawn": round(total_withdrawn, 2),
            "closing_balance": round(closing, 2),
        },
    }
