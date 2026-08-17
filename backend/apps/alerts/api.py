"""
Alert API endpoints for ML-Auditor.
"""

from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.utils import timezone
from ninja import Query, Router
from ninja.errors import HttpError

from .models import AgentAlert
from .schemas import AlertListResponse, AlertResponse, AlertStats, AlertUpdate

router = Router()


@router.get("/", response=AlertListResponse)
def list_alerts(
    request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    severity: str = Query(None),
    status: str = Query(None),
):
    """List alerts for current user."""
    queryset = AgentAlert.objects.filter(user=request.auth)

    if severity:
        queryset = queryset.filter(severity=severity)
    if status:
        queryset = queryset.filter(status=status)

    # Get counts by severity
    severity_counts = queryset.values("severity").annotate(count=Count("id"))
    severity_map = {item["severity"]: item["count"] for item in severity_counts}

    paginator = Paginator(queryset, page_size)
    page_obj = paginator.get_page(page)

    return AlertListResponse(
        items=list(page_obj),
        total=paginator.count,
        page=page,
        pages=paginator.num_pages,
        critical_count=severity_map.get("critical", 0),
        high_count=severity_map.get("high", 0),
        medium_count=severity_map.get("medium", 0),
        low_count=severity_map.get("low", 0),
    )


@router.get("/unified")
def unified_alerts(request, limit: int = Query(50)):
    """Combined feed of agent alerts + Jira issues (single notifications view)."""
    from datetime import datetime, timezone as dt_timezone

    items = []

    for alert in AgentAlert.objects.filter(user=request.auth)[:limit]:
        items.append(
            {
                "id": str(alert.id),
                "source": "agent",
                "title": alert.title,
                "description": alert.description,
                "severity": alert.severity,
                "status": alert.status,
                "created_at": alert.created_at.isoformat(),
                "url": None,
            }
        )

    jira_error = None
    jira_connected = bool(request.auth.jira_site_url and request.auth.jira_api_token)
    if jira_connected:
        try:
            from apps.users.services.jira_client import JiraClient

            client = JiraClient(
                site_url=request.auth.jira_site_url,
                email=request.auth.jira_email,
                api_token=request.auth.jira_api_token,
            )
            issues = client.get_issues(
                jql='statusCategory != "Done" ORDER BY updated DESC',
                max_results=limit,
            )
            for issue in issues:
                items.append(
                    {
                        "id": issue["key"],
                        "source": "jira",
                        "title": f"[{issue['key']}] {issue['summary']}",
                        "description": (issue.get("description") or "")[:500],
                        "severity": _jira_priority(issue.get("priority", "")),
                        "status": issue.get("status", ""),
                        "created_at": issue.get("created", ""),
                        "url": issue.get("url"),
                    }
                )
        except Exception as e:
            jira_error = str(e)

    def _sort_key(item):
        raw = item["created_at"]
        try:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=dt_timezone.utc)
            return parsed.timestamp()
        except Exception:
            return 0.0

    items.sort(key=_sort_key, reverse=True)
    return {
        "items": items[:limit],
        "total": len(items),
        "jira_connected": jira_connected,
        "jira_error": jira_error,
    }


def _jira_priority(priority: str) -> str:
    if not priority:
        return "medium"
    p = priority.lower()
    if p in ("highest", "high"):
        return "high"
    if p in ("lowest", "low"):
        return "low"
    if p == "critical":
        return "critical"
    return "medium"


@router.get("/stats", response=AlertStats)
def get_alert_stats(request):
    """Get alert statistics for current user."""
    queryset = AgentAlert.objects.filter(user=request.auth)

    stats = queryset.aggregate(
        total=Count("id"),
        pending=Count("id", filter=Q(status="pending")),
        acknowledged=Count("id", filter=Q(status="acknowledged")),
        executed=Count("id", filter=Q(status="executed")),
        dismissed=Count("id", filter=Q(status="dismissed")),
    )

    severity_counts = queryset.values("severity").annotate(count=Count("id"))
    by_severity = {item["severity"]: item["count"] for item in severity_counts}

    return AlertStats(
        total=stats["total"],
        pending=stats["pending"],
        acknowledged=stats["acknowledged"],
        executed=stats["executed"],
        dismissed=stats["dismissed"],
        by_severity=by_severity,
    )


@router.get("/{alert_id}", response=AlertResponse)
def get_alert(request, alert_id: str):
    """Get alert by ID."""
    try:
        alert = AgentAlert.objects.get(id=alert_id, user=request.auth)
        return alert
    except AgentAlert.DoesNotExist:
        raise HttpError(404, "Alert not found")


@router.put("/{alert_id}", response=AlertResponse)
def update_alert(request, alert_id: str, payload: AlertUpdate):
    """Update alert status."""
    try:
        alert = AgentAlert.objects.get(id=alert_id, user=request.auth)
        for field, value in payload.dict(exclude_unset=True).items():
            setattr(alert, field, value)
        alert.save()
        return alert
    except AgentAlert.DoesNotExist:
        raise HttpError(404, "Alert not found")


@router.post("/{alert_id}/acknowledge")
def acknowledge_alert(request, alert_id: str):
    """Acknowledge an alert."""
    try:
        alert = AgentAlert.objects.get(id=alert_id, user=request.auth)
        if alert.status == "pending":
            alert.status = "acknowledged"
            alert.acknowledged_at = timezone.now()
            alert.save()
            return {"success": True}
        else:
            raise HttpError(400, "Alert already acknowledged")
    except AgentAlert.DoesNotExist:
        raise HttpError(404, "Alert not found")


@router.post("/{alert_id}/execute")
def execute_alert(request, alert_id: str):
    """Execute alert action."""
    try:
        alert = AgentAlert.objects.get(id=alert_id, user=request.auth)
        if alert.status in ["pending", "acknowledged"]:
            alert.status = "executed"
            alert.executed_at = timezone.now()
            alert.save()
            # TODO: Trigger action based on action_payload
            return {"success": True}
        else:
            raise HttpError(400, "Alert already executed")
    except AgentAlert.DoesNotExist:
        raise HttpError(404, "Alert not found")


@router.post("/{alert_id}/dismiss")
def dismiss_alert(request, alert_id: str):
    """Dismiss an alert."""
    try:
        alert = AgentAlert.objects.get(id=alert_id, user=request.auth)
        alert.status = "dismissed"
        alert.save()
        return {"success": True}
    except AgentAlert.DoesNotExist:
        raise HttpError(404, "Alert not found")
