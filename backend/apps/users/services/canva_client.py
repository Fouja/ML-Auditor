"""
Canva Connect API client.
Handles design access, brand monitoring, and competitor tracking.
"""

import logging
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

CANVA_API_BASE = "https://api.canva.com/rest/v1"


class CanvaClient:
    """
    Client for Canva Connect API.
    Supports OAuth2 authentication and design operations.
    """

    def __init__(self, access_token: str):
        self.access_token = access_token
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }
        )

    def _request(self, method: str, path: str, **kwargs) -> Dict[str, Any]:
        url = f"{CANVA_API_BASE}{path}"
        try:
            resp = self.session.request(method, url, timeout=30, **kwargs)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            logger.error(f"Canva API error: {e}")
            if hasattr(e, "response") and e.response is not None:
                logger.error(f"Response: {e.response.text}")
            raise

    # ─── Designs ─────────────────────────────────────────────────────

    def get_designs(
        self,
        query: Optional[str] = None,
        owner_team_id: Optional[str] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Get user's designs."""
        params: Dict[str, Any] = {"query": query or ""}
        if owner_team_id:
            params["owner_team_id"] = owner_team_id
        data = self._request("GET", "/designs", params=params)
        return data.get("items", [])

    def get_design(self, design_id: str) -> Dict[str, Any]:
        """Get a single design by ID."""
        return self._request("GET", f"/designs/{design_id}")

    def create_design(
        self,
        design_type: str,
        title: str,
        width: int = 800,
        height: int = 600,
    ) -> Dict[str, Any]:
        """Create a new design."""
        payload = {
            "design_type": design_type,
            "title": title,
            "width": width,
            "height": height,
        }
        return self._request("POST", "/designs", json=payload)

    def export_design(
        self,
        design_id: str,
        format: str = "png",
        quality: str = "regular",
        width: Optional[int] = None,
        height: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Export a design to file."""
        payload: Dict[str, Any] = {"format": format, "quality": quality}
        if width:
            payload["width"] = width
        if height:
            payload["height"] = height
        return self._request("POST", f"/designs/{design_id}/export", json=payload)

    def get_export_asset(self, design_id: str, job_id: str) -> Dict[str, Any]:
        """Get export job result."""
        return self._request("GET", f"/designs/{design_id}/export/{job_id}")

    # ─── Folders ─────────────────────────────────────────────────────

    def get_folders(self, parent_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get design folders."""
        params = {}
        if parent_id:
            params["parent_folder_id"] = parent_id
        data = self._request("GET", "/folders", params=params)
        return data.get("items", [])

    # ─── Brand Templates ─────────────────────────────────────────────

    def get_brand_templates(self) -> List[Dict[str, Any]]:
        """Get brand templates."""
        data = self._request("GET", "/brand-templates")
        return data.get("items", [])

    # ─── Comments & Activity ─────────────────────────────────────────

    def get_design_comments(self, design_id: str) -> List[Dict[str, Any]]:
        """Get comments on a design."""
        data = self._request("GET", f"/designs/{design_id}/comments")
        return data.get("items", [])

    # ─── User & Team Info ────────────────────────────────────────────

    def get_me(self) -> Dict[str, Any]:
        """Get current user info."""
        return self._request("GET", "/me")

    # ─── Competitor Monitoring Helpers ────────────────────────────────

    def search_public_designs(
        self,
        keywords: List[str],
        category: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search Canva's template library for competitor-style designs.
        Useful for monitoring trending design patterns.
        """
        results = []
        for keyword in keywords:
            try:
                data = self._request(
                    "GET",
                    "/templates",
                    params={"query": keyword, "category": category or ""},
                )
                templates = data.get("items", [])
                results.extend(templates)
            except Exception as e:
                logger.warning(f"Template search failed for '{keyword}': {e}")
        return results

    def get_design_analytics(self, design_id: str) -> Dict[str, Any]:
        """
        Get design engagement stats (views, edits).
        Canva's public API may not expose full analytics;
        this is a placeholder for extended API or scraping.
        """
        design = self.get_design(design_id)
        return {
            "design_id": design_id,
            "title": design.get("title", ""),
            "created_at": design.get("created_at"),
            "updated_at": design.get("updated_at"),
            "status": design.get("status"),
            "has_comments": len(self.get_design_comments(design_id)) > 0,
        }

    def track_competitor_keywords(
        self,
        keywords: List[str],
        max_results: int = 20,
    ) -> Dict[str, Any]:
        """
        Monitor design trends by tracking competitor keywords.
        Returns trending templates matching the keywords.
        """
        all_templates = self.search_public_designs(keywords)
        trending = []
        for t in all_templates[:max_results]:
            trending.append(
                {
                    "id": t.get("id"),
                    "title": t.get("title", ""),
                    "thumbnail": t.get("thumbnail", {}).get("url", ""),
                    "created_at": t.get("created_at"),
                    "tags": t.get("tags", []),
                }
            )
        return {
            "keywords": keywords,
            "results_count": len(trending),
            "templates": trending,
        }
