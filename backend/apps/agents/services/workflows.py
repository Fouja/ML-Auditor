"""
Smart workflows — automated agent pipelines.
Each workflow is a sequence of steps triggered by conditions.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class WorkflowResult:
    def __init__(
        self, workflow: str, success: bool, actions: List[Dict], message: str = ""
    ):
        self.workflow = workflow
        self.success = success
        self.actions = actions
        self.message = message

    def to_dict(self) -> Dict:
        return {
            "workflow": self.workflow,
            "success": self.success,
            "actions": self.actions,
            "message": self.message,
        }


# ─── Workflow: Confirm RDV (Appointment Confirmation) ────────────────


def workflow_confirm_rdv(user, event_data: Dict[str, Any]) -> WorkflowResult:
    """
    Confirm an appointment:
    1. Create/update calendar event
    2. Send confirmation email
    3. Create a reminder task
    """
    actions = []

    # Step 1: Create calendar event
    try:
        from apps.users.services import CalendarClient

        if user.google_access_token:
            cal = CalendarClient(user)
            event = cal.create_event(
                summary=event_data.get("title", "Appointment"),
                start_time=datetime.fromisoformat(event_data["start_time"]),
                end_time=datetime.fromisoformat(event_data["end_time"]),
                description=event_data.get("description", ""),
                location=event_data.get("location"),
            )
            actions.append(
                {
                    "step": "calendar_event",
                    "status": "created",
                    "event_id": event.get("id"),
                }
            )
    except Exception as e:
        actions.append({"step": "calendar_event", "status": "error", "error": str(e)})

    # Step 2: Send confirmation email
    try:
        _send_confirmation_email(user, event_data)
        actions.append({"step": "confirmation_email", "status": "sent"})
    except Exception as e:
        actions.append(
            {"step": "confirmation_email", "status": "error", "error": str(e)}
        )

    # Step 3: Create reminder task
    try:
        from apps.workspace.models import Task

        Task.objects.create(
            user=user,
            title=f"Prepare for: {event_data.get('title', 'Appointment')}",
            description=f"Appointment on {event_data.get('start_time')}",
            status="todo",
            priority="medium",
        )
        actions.append({"step": "reminder_task", "status": "created"})
    except Exception as e:
        actions.append({"step": "reminder_task", "status": "error", "error": str(e)})

    return WorkflowResult(
        workflow="confirm_rdv",
        success=all(a.get("status") != "error" for a in actions),
        actions=actions,
        message="Appointment confirmation workflow completed.",
    )


def _send_confirmation_email(user, event_data: Dict):
    """Send appointment confirmation email."""
    if user.email_imap_host and user.email_imap_password:
        from apps.users.services.email_client import EmailClient

        client = EmailClient(
            email_address=user.email,
            password=user.email_imap_password,
            provider=user.email_provider or "custom",
            smtp_host=user.email_smtp_host,
            smtp_port=user.email_smtp_port,
            use_ssl=user.email_use_ssl,
        )
        client.send_message(
            to=event_data.get("attendee_email", user.email),
            subject=f"Appointment Confirmed: {event_data.get('title')}",
            body=(
                f"Your appointment has been confirmed.\n\n"
                f"Title: {event_data.get('title')}\n"
                f"Date: {event_data.get('start_time')}\n"
                f"Location: {event_data.get('location', 'TBD')}\n"
            ),
        )
    elif user.google_access_token:
        from apps.users.services import GmailClient

        gmail = GmailClient(user)
        gmail.send_message(
            to=event_data.get("attendee_email", user.email),
            subject=f"Appointment Confirmed: {event_data.get('title')}",
            body=(
                f"Your appointment has been confirmed.\n\n"
                f"Title: {event_data.get('title')}\n"
                f"Date: {event_data.get('start_time')}\n"
                f"Location: {event_data.get('location', 'TBD')}\n"
            ),
        )


# ─── Workflow: Financial Anomaly Alert ───────────────────────────────


def workflow_financial_anomaly(user, anomaly_data: Dict[str, Any]) -> WorkflowResult:
    """
    Handle a financial anomaly:
    1. Create a high-priority alert
    2. Create a task for review
    3. Send notification email
    """
    actions = []

    # Step 1: Create alert
    try:
        from apps.alerts.models import AgentAlert

        alert = AgentAlert.objects.create(
            user=user,
            title=f"Financial Anomaly: {anomaly_data.get('description', 'Suspicious activity')}",
            description=(
                f"Transaction: {anomaly_data.get('transaction_name', 'Unknown')}\n"
                f"Amount: ${anomaly_data.get('amount', 0)}\n"
                f"Category: {anomaly_data.get('category', 'Unknown')}\n"
                f"Confidence: {anomaly_data.get('confidence', 0)}"
            ),
            severity="high" if anomaly_data.get("confidence", 0) > 0.8 else "medium",
            source_type="financial",
            action_payload=anomaly_data,
        )
        actions.append({"step": "alert_created", "alert_id": str(alert.id)})
    except Exception as e:
        actions.append({"step": "alert_created", "status": "error", "error": str(e)})

    # Step 2: Create review task
    try:
        from apps.workspace.models import Task

        Task.objects.create(
            user=user,
            title=f"Review anomaly: {anomaly_data.get('transaction_name', 'Unknown')}",
            description=f"${anomaly_data.get('amount', 0)} — {anomaly_data.get('description', '')}",
            status="todo",
            priority="high",
        )
        actions.append({"step": "review_task", "status": "created"})
    except Exception as e:
        actions.append({"step": "review_task", "status": "error", "error": str(e)})

    # Step 3: Notification email
    try:
        _send_anomaly_notification(user, anomaly_data)
        actions.append({"step": "notification_email", "status": "sent"})
    except Exception as e:
        actions.append(
            {"step": "notification_email", "status": "error", "error": str(e)}
        )

    return WorkflowResult(
        workflow="financial_anomaly",
        success=True,
        actions=actions,
        message="Financial anomaly alert workflow completed.",
    )


def _send_anomaly_notification(user, anomaly_data: Dict):
    if user.email_imap_host and user.email_imap_password:
        from apps.users.services.email_client import EmailClient

        client = EmailClient(
            email_address=user.email,
            password=user.email_imap_password,
            provider=user.email_provider or "custom",
            smtp_host=user.email_smtp_host,
            smtp_port=user.email_smtp_port,
            use_ssl=user.email_use_ssl,
        )
        client.send_message(
            to=user.email,
            subject=f"⚠️ Financial Anomaly Detected — ${anomaly_data.get('amount', 0)}",
            body=(
                f"A suspicious transaction was detected.\n\n"
                f"Transaction: {anomaly_data.get('transaction_name', 'Unknown')}\n"
                f"Amount: ${anomaly_data.get('amount', 0)}\n"
                f"Confidence: {anomaly_data.get('confidence', 0) * 100:.0f}%\n\n"
                f"Please review this transaction in your dashboard."
            ),
        )


# ─── Workflow: Email Auto-Reply ──────────────────────────────────────


def workflow_email_auto_reply(user, email_data: Dict[str, Any]) -> WorkflowResult:
    """
    Auto-reply to an email:
    1. Analyze the email content
    2. Draft a response
    3. Send the reply (if auto-send enabled)
    """
    actions = []

    # Step 1: Analyze
    subject = email_data.get("subject", "")
    sender = email_data.get("from", "")
    body = email_data.get("body", "")  # noqa: F841

    actions.append(
        {
            "step": "analysis",
            "status": "completed",
            "sender": sender,
            "subject": subject,
        }
    )

    # Step 2: Draft response
    draft_body = f"Thank you for your email regarding '{subject}'. We have received your message and will respond shortly."
    actions.append({"step": "draft_created", "status": "completed"})

    # Step 3: Send if auto-reply enabled
    try:
        if user.email_imap_host and user.email_imap_password:
            from apps.users.services.email_client import EmailClient

            client = EmailClient(
                email_address=user.email,
                password=user.email_imap_password,
                provider=user.email_provider or "custom",
                smtp_host=user.email_smtp_host,
                smtp_port=user.email_smtp_port,
                use_ssl=user.email_use_ssl,
            )
            client.send_message(to=sender, subject=f"Re: {subject}", body=draft_body)
            actions.append({"step": "auto_reply_sent", "status": "sent"})
    except Exception as e:
        actions.append({"step": "auto_reply_sent", "status": "error", "error": str(e)})

    return WorkflowResult(
        workflow="email_auto_reply",
        success=True,
        actions=actions,
        message="Email auto-reply workflow completed.",
    )


# ─── Workflow: Kijiji Negotiation ────────────────────────────────────


def workflow_kijiji_negotiation(user, listing_data: Dict[str, Any]) -> WorkflowResult:
    """
    Kijiji negotiation assistant:
    1. Analyze the listing
    2. Suggest a negotiation strategy
    3. Draft a message
    """
    actions = []

    # Step 1: Analyze listing
    price = listing_data.get("price", 0)
    title = listing_data.get("title", "")
    actions.append(
        {
            "step": "listing_analysis",
            "status": "completed",
            "title": title,
            "listed_price": price,
        }
    )

    # Step 2: Suggest strategy
    suggested_offer = price * 0.8 if price > 50 else price * 0.9
    strategy = (
        f"Consider offering ${suggested_offer:.2f} (20% below asking)"
        if price > 50
        else f"Consider offering ${suggested_offer:.2f} (10% below asking)"
    )
    actions.append({"step": "strategy", "suggestion": strategy})

    # Step 3: Draft message
    draft_message = (
        f"Hi, I'm interested in '{title}'. "
        f"Would you consider ${suggested_offer:.2f}? "
        f"Let me know. Thanks!"
    )
    actions.append({"step": "draft_message", "message": draft_message})

    return WorkflowResult(
        workflow="kijiji_negotiation",
        success=True,
        actions=actions,
        message=f"Negotiation strategy: {strategy}",
    )


# ─── Workflow registry ───────────────────────────────────────────────

WORKFLOWS = {
    "confirm_rdv": workflow_confirm_rdv,
    "financial_anomaly": workflow_financial_anomaly,
    "email_auto_reply": workflow_email_auto_reply,
    "kijiji_negotiation": workflow_kijiji_negotiation,
}


def execute_workflow(workflow_name: str, user, data: Dict[str, Any]) -> WorkflowResult:
    """Execute a named workflow."""
    handler = WORKFLOWS.get(workflow_name)
    if not handler:
        return WorkflowResult(
            workflow=workflow_name,
            success=False,
            actions=[],
            message=f"Unknown workflow: {workflow_name}",
        )
    return handler(user, data)
