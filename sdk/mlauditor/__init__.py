"""
ML-Auditor Python SDK
Provides a client library for the ML-Auditor API.
"""

import requests
from typing import Any, Dict, Optional


class MLAuditorClient:
    """Client for the ML-Auditor API."""

    def __init__(self, base_url: str = "http://localhost:8000", token: Optional[str] = None):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        if token:
            self.session.headers["Authorization"] = f"Bearer {token}"

    def login(self, email: str, password: str) -> Dict[str, Any]:
        """Authenticate and store JWT tokens."""
        resp = self.session.post(f"{self.base_url}/api/users/login", json={
            "email": email, "password": password,
        })
        resp.raise_for_status()
        data = resp.json()
        self.session.headers["Authorization"] = f"Bearer {data['access']}"
        return data

    def register(self, email: str, username: str, password: str, **kwargs) -> Dict[str, Any]:
        """Register a new user."""
        resp = self.session.post(f"{self.base_url}/api/users/register", json={
            "email": email, "username": username, "password": password, **kwargs,
        })
        resp.raise_for_status()
        data = resp.json()
        self.session.headers["Authorization"] = f"Bearer {data['access']}"
        return data

    # ── Tasks ──────────────────────────────────────────────

    def list_tasks(self, status: Optional[str] = None) -> list:
        params = {}
        if status:
            params["status"] = status
        return self.session.get(f"{self.base_url}/api/workspace/tasks", params=params).json()

    def create_task(self, title: str, status: str = "todo", priority: str = "medium") -> Dict:
        return self.session.post(f"{self.base_url}/api/workspace/tasks", json={
            "title": title, "status": status, "priority": priority,
        }).json()

    def update_task(self, task_id: str, **kwargs) -> Dict:
        return self.session.put(f"{self.base_url}/api/workspace/tasks/{task_id}", json=kwargs).json()

    def delete_task(self, task_id: str) -> Dict:
        return self.session.delete(f"{self.base_url}/api/workspace/tasks/{task_id}").json()

    # ── Events ─────────────────────────────────────────────

    def list_events(self, start: Optional[str] = None, end: Optional[str] = None) -> list:
        params = {}
        if start:
            params["start"] = start
        if end:
            params["end"] = end
        return self.session.get(f"{self.base_url}/api/workspace/events", params=params).json()

    def create_event(self, title: str, start_time: str, end_time: str, **kwargs) -> Dict:
        return self.session.post(f"{self.base_url}/api/workspace/events", json={
            "title": title, "start_time": start_time, "end_time": end_time, **kwargs,
        }).json()

    # ── Agent ──────────────────────────────────────────────

    def chat(self, message: str, agent_type: str = "general") -> Dict:
        return self.session.post(f"{self.base_url}/api/agents/chat", json={
            "content": message, "agent_type": agent_type,
        }).json()

    def agent_status(self) -> Dict:
        return self.session.get(f"{self.base_url}/api/agents/status").json()

    def list_workflows(self) -> Dict:
        return self.session.get(f"{self.base_url}/api/agents/workflows").json()

    def execute_workflow(self, workflow: str, data: Dict) -> Dict:
        return self.session.post(f"{self.base_url}/api/agents/workflows/execute", json={
            "workflow": workflow, "data": data,
        }).json()

    # ── Integrations ───────────────────────────────────────

    def integration_status(self) -> Dict:
        return self.session.get(f"{self.base_url}/api/integrations/status").json()

    def search_kijiji(self, query: str, **kwargs) -> Dict:
        return self.session.post(f"{self.base_url}/api/integrations/kijiji/search", json={
            "query": query, **kwargs,
        }).json()
