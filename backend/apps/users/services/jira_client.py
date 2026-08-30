"""
Jira REST API client for ML-Auditor.
Uses Basic Auth (email + API token) against Jira Cloud REST API v3.
"""

import base64
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


class JiraClient:
    """
    Client for the Jira Cloud REST API v3.

    Supports both Basic Auth (email + API token) and OAuth 2.0 bearer tokens.

    Basic auth:
        JiraClient(site_url, email, api_token)

    OAuth 2.0:
        JiraClient(site_url, oauth_token=oauth_access_token)
    """

    def __init__(
        self,
        site_url: str,
        email: Optional[str] = None,
        api_token: Optional[str] = None,
        oauth_token: Optional[str] = None,
    ):
        self.site_url = site_url.rstrip("/")
        self.email = email
        self.api_token = api_token
        self.oauth_token = oauth_token

        if oauth_token:
            auth_header = f"Bearer {oauth_token}"
        elif email and api_token:
            auth_str = base64.b64encode(f"{email}:{api_token}".encode()).decode()
            auth_header = f"Basic {auth_str}"
        else:
            raise ValueError("JiraClient requires either (email, api_token) or oauth_token")

        self._client = httpx.Client(
            base_url=self.site_url,
            headers={
                "Authorization": auth_header,
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            timeout=30,
        )

    # ─── Connection test ─────────────────────────────────────────────

    def test_connection(self) -> Dict[str, Any]:
        """Verify credentials by fetching the current user."""
        try:
            resp = self._client.get("/rest/api/3/myself")
            resp.raise_for_status()
            user = resp.json()
            return {
                "success": True,
                "account_id": user.get("accountId"),
                "display_name": user.get("displayName"),
                "email": user.get("emailAddress"),
            }
        except httpx.HTTPStatusError as e:
            return {"success": False, "error": f"HTTP {e.response.status_code}: {e.response.text[:200]}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ─── Projects ────────────────────────────────────────────────────

    def get_projects(self) -> List[Dict[str, Any]]:
        """List all projects the user has access to."""
        resp = self._client.get("/rest/api/3/project")
        resp.raise_for_status()
        projects = resp.json()
        return [
            {
                "id": p["id"],
                "key": p["key"],
                "name": p.get("name", ""),
                "project_type_key": p.get("projectTypeKey", ""),
                "lead": p.get("lead", {}).get("displayName", ""),
                "avatar_url": p.get("avatarUrls", {}).get("48x48", ""),
            }
            for p in projects
        ]

    # ─── Issues ──────────────────────────────────────────────────────

    def get_issues(
        self,
        project_key: Optional[str] = None,
        jql: Optional[str] = None,
        max_results: int = 50,
        fields: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Search issues using JQL. Returns paginated results.

        Note: since Atlassian removed the plain POST /rest/api/3/search
        endpoint (410 Gone, CHANGE-2024-01) in favour of /search/jql, the
        query must be bounded — the new endpoint rejects unbounded JQL.
        """
        if not jql and project_key:
            jql = f'project = "{project_key}" ORDER BY updated DESC'
        elif not jql:
            jql = "created >= -180d ORDER BY updated DESC"

        default_fields = [
            "summary", "description", "status", "priority", "assignee",
            "reporter", "created", "updated", "duedate", "labels",
            "issuetype", "project", "fixVersions", "components",
        ]

        resp = self._client.post(
            "/rest/api/3/search/jql",
            json={
                "jql": jql,
                "maxResults": max_results,
                "fields": fields or default_fields,
            },
        )
        resp.raise_for_status()
        data = resp.json()

        return [self._normalize_issue(issue) for issue in data.get("issues", [])]

    def get_issue(self, issue_key: str) -> Dict[str, Any]:
        """Get a single issue by key (e.g. 'PROJ-123')."""
        resp = self._client.get(f"/rest/api/3/issue/{issue_key}")
        resp.raise_for_status()
        return self._normalize_issue(resp.json())

    @staticmethod
    def _adf_to_text(value: Any) -> str:
        """Flatten Jira ADF (Atlassian Document Format) JSON into plain text."""
        if value is None:
            return ""
        if isinstance(value, str):
            return value
        if isinstance(value, dict):
            content = value.get("content") or []
            text = value.get("text")
            if text:
                return str(text)
            parts = []
            for node in content:
                parts.append(JiraClient._adf_to_text(node))
            return "\n".join(p for p in parts if p)
        if isinstance(value, list):
            return "\n".join(
                p for p in (JiraClient._adf_to_text(v) for v in value) if p
            )
        return str(value)

    def _normalize_issue(self, issue: Dict) -> Dict[str, Any]:
        """Extract flattened fields from Jira issue response."""
        fields = issue.get("fields", {})
        assignee = fields.get("assignee") or {}
        reporter = fields.get("reporter") or {}
        status = fields.get("status") or {}
        priority = fields.get("priority") or {}
        issue_type = fields.get("issuetype") or {}
        project = fields.get("project") or {}
        return {
            "id": issue["id"],
            "key": issue["key"],
            "self": issue.get("self", ""),
            "summary": fields.get("summary", ""),
            "description": self._adf_to_text(fields.get("description")),
            "status": status.get("name", ""),
            "status_category": status.get("statusCategory", {}).get("name", ""),
            "priority": priority.get("name", ""),
            "issue_type": issue_type.get("name", ""),
            "project_key": project.get("key", ""),
            "project_name": project.get("name", ""),
            "assignee_display": assignee.get("displayName", ""),
            "assignee_email": assignee.get("emailAddress", ""),
            "reporter_display": reporter.get("displayName", ""),
            "reporter_email": reporter.get("emailAddress", ""),
            "labels": fields.get("labels", []),
            "components": [c.get("name", "") for c in fields.get("components", [])],
            "fix_versions": [v.get("name", "") for v in fields.get("fixVersions", [])],
            "created": fields.get("created", ""),
            "updated": fields.get("updated", ""),
            "due_date": fields.get("duedate"),
            "url": f"{self.site_url}/browse/{issue['key']}",
        }

    # ─── Sprints (if Jira Software is available) ──────────────────────

    def get_sprints(self, board_id: int, max_results: int = 50) -> List[Dict[str, Any]]:
        """Get sprints for a given board."""
        try:
            resp = self._client.get(
                f"/rest/agile/1.0/board/{board_id}/sprint",
                params={"maxResults": max_results},
            )
            resp.raise_for_status()
            return resp.json().get("values", [])
        except Exception as e:
            logger.warning(f"Failed to fetch sprints: {e}")
            return []

    def get_boards(self) -> List[Dict[str, Any]]:
        """Get all Scrum/Kanban boards."""
        try:
            resp = self._client.get(
                "/rest/agile/1.0/board",
                params={"maxResults": 50},
            )
            resp.raise_for_status()
            return resp.json().get("values", [])
        except Exception as e:
            logger.warning(f"Failed to fetch boards: {e}")
            return []

    # ─── Search (for RAG) ─────────────────────────────────────────────

    def search_for_rag(self, query: str, max_results: int = 20) -> List[Dict[str, Any]]:
        """Search issues by free-text and return text content suitable for RAG ingestion."""
        jql = f'text ~ "{query}" ORDER BY updated DESC'
        issues = self.get_issues(jql=jql, max_results=max_results)
        return [self._rag_result(issue) for issue in issues]

    def issues_for_rag(self, project_key: str, max_results: int = 50) -> List[Dict[str, Any]]:
        """Return RAG-ready text content for issues in a project."""
        issues = self.get_issues(project_key=project_key, max_results=max_results)
        return [self._rag_result(issue) for issue in issues]

    def _rag_result(self, issue: Dict[str, Any]) -> Dict[str, Any]:
        """Build a RAG-ready snippet from a normalized issue."""
        text_parts = [
            f"Issue: {issue['key']}",
            f"Summary: {issue['summary']}",
            f"Status: {issue['status']}",
            f"Priority: {issue['priority']}",
            f"Project: {issue['project_name']}",
            f"Assignee: {issue['assignee_display']}",
        ]
        if issue["description"]:
            text_parts.append(f"Description: {issue['description'][:1000]}")
        if issue["labels"]:
            text_parts.append(f"Labels: {', '.join(issue['labels'])}")
        if issue["due_date"]:
            text_parts.append(f"Due: {issue['due_date']}")
        return {
            "key": issue["key"],
            "url": issue["url"],
            "text": "\n".join(text_parts),
            "updated": issue["updated"],
        }

    def close(self):
        self._client.close()
