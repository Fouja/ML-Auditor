"""
Client for the Web Tools microservice (Agent-Reach: Jina Reader web read,
DuckDuckGo/Exa search, RSS parsing). The chatbot uses these for live
internet access.
"""

import asyncio
import logging

import httpx
from django.conf import settings

logger = logging.getLogger(__name__)

BASE_URL = getattr(settings, "WEB_TOOLS_URL", "http://localhost:8090")
TIMEOUT = 40


async def web_search(query: str, num_results: int = 5) -> str:
    """Search the live web and return results (markdown/JSON) as text."""
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.post(
                f"{BASE_URL}/search",
                json={"query": query, "num_results": num_results},
            )
            resp.raise_for_status()
            data = resp.json()
        if isinstance(data.get("results"), str):
            return data["results"]
        results = data.get("results", [])
        if isinstance(results, list):
            lines = []
            for r in results:
                title = r.get("title", "")
                url = r.get("url", "")
                snippet = (r.get("snippet") or "")[:300]
                lines.append(f"- {title}\n  URL: {url}\n  {snippet}")
            return "\n".join(lines)
        return str(results)
    except Exception as e:
        logger.warning(f"web_search failed: {e}")
        return f"Search failed: {e}"


async def fetch_webpage(url: str) -> str:
    """Fetch a URL and return clean markdown."""
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.post(f"{BASE_URL}/fetch", json={"url": url})
            resp.raise_for_status()
            return resp.json().get("markdown", "")
    except Exception as e:
        logger.warning(f"fetch_webpage failed: {e}")
        return f"Fetch failed: {e}"


async def scrape_page(url: str) -> dict:
    """Fetch a page with extracted title/content/image/summary metadata."""
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.post(f"{BASE_URL}/scrape", json={"url": url})
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.warning(f"scrape_page failed: {e}")
        return {"url": url, "error": str(e)}


async def parse_rss(feed_url: str) -> list:
    """Parse an RSS/Atom feed and return entries."""
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.post(f"{BASE_URL}/rss", json={"feed_url": feed_url})
            resp.raise_for_status()
            return resp.json().get("entries", [])
    except Exception as e:
        logger.warning(f"parse_rss failed: {e}")
        return []


async def agent_reach_status() -> dict:
    """Health/status report from Agent-Reach."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{BASE_URL}/agent-reach/doctor")
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        return {"error": str(e)}


def web_search_sync(query: str, num_results: int = 5) -> str:
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
    return loop.run_until_complete(web_search(query, num_results))
