"""
Web Tools microservice — wraps Agent-Reach (Jina Reader web channel + feedparser
RSS routing) and a keyless Jina search fallback behind a small HTTP API so the
ML-Auditor chatbot can read and search the live internet.

Endpoints:
    GET  /health              liveness
    GET  /agent-reach/doctor  agent-reach install/health report
    POST /search              {query, num_results}  -> web search results
    POST /fetch               {url}                 -> clean markdown of a page
    POST /scrape              {url}                 -> title/content/image/etc.
    POST /rss                 {feed_url}            -> parsed RSS/Atom entries
"""

import os
import re
import time
import logging
from urllib.parse import quote

logger = logging.getLogger("web-tools")

import httpx
from bs4 import BeautifulSoup
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="ML-Auditor Web Tools", version="1.0.0")

EXA_API_KEY = os.environ.get("EXA_API_KEY", "")
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
MAX_MARKDOWN = 15000
MAX_SEARCH = 12000

from agent_reach.channels.web import WebChannel  # noqa: E402

web = WebChannel()


class SearchRequest(BaseModel):
    query: str
    num_results: int = 5


class UrlRequest(BaseModel):
    url: str


class RSSRequest(BaseModel):
    feed_url: str


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "web-tools",
        "search_provider": "exa" if EXA_API_KEY else "duckduckgo-via-jina-reader",
    }


@app.get("/agent-reach/doctor")
def doctor():
    try:
        from agent_reach.config import Config
        from agent_reach.core import AgentReach

        eyes = AgentReach(Config(read_only=True))
        return eyes.doctor_report()
    except Exception as e:
        return {"error": str(e)}


@app.post("/search")
async def search(req: SearchRequest):
    query = req.query.strip()
    if not query:
        raise HTTPException(400, "query is required")
    try:
        if EXA_API_KEY:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    "https://api.exa.ai/search",
                    headers={
                        "x-api-key": EXA_API_KEY,
                        "Content-Type": "application/json",
                    },
                    json={
                        "query": query,
                        "numResults": max(1, min(req.num_results, 10)),
                        "text": True,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
            results = []
            for r in data.get("results", []):
                results.append(
                    {
                        "title": r.get("title", ""),
                        "url": r.get("url", ""),
                        "snippet": (r.get("text") or "")[:400],
                    }
                )
            return {"query": query, "provider": "exa", "results": results}
        # Keyless fallback: route a DuckDuckGo query through Jina Reader
        markdown = web.read(f"https://html.duckduckgo.com/html/?q={quote(query)}")
        return {
            "query": query,
            "provider": "duckduckgo-via-jina-reader",
            "results": _clean_ddg(markdown)[:MAX_SEARCH],
        }
    except Exception as e:
        raise HTTPException(502, f"search failed: {e}")


@app.post("/fetch")
async def fetch(req: UrlRequest):
    if not req.url.startswith(("http://", "https://")):
        raise HTTPException(400, "url must start with http:// or https://")
    try:
        markdown = web.read(req.url)
        return {"url": req.url, "provider": "jina-reader", "markdown": markdown[:MAX_MARKDOWN]}
    except Exception as e:
        raise HTTPException(502, f"fetch failed: {e}")


@app.post("/scrape")
async def scrape(req: UrlRequest):
    """Fetch a page, extract title/content/summary/image metadata."""
    url = req.url
    if not url.startswith(("http://", "https://")):
        raise HTTPException(400, "url must start with http:// or https://")

    title = ""
    image_url = ""
    author = ""
    published_at = ""
    content = ""
    try:
        content = web.read(url)
    except Exception:
        content = ""

    try:
        async with httpx.AsyncClient(
            timeout=20, follow_redirects=True, headers={"User-Agent": UA}
        ) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                title = (
                    soup.find("meta", property="og:title") or {}
                ).get("content") or (soup.title.get_text().strip() if soup.title else "")
                og_image = (soup.find("meta", property="og:image") or {}).get(
                    "content", ""
                )
                if og_image:
                    image_url = og_image if og_image.startswith("http") else url + og_image
                author = (
                    (soup.find("meta", property="article:author") or {}).get("content", "")
                    or (soup.find("meta", attrs={"name": "author"}) or {}).get("content", "")
                    or ""
                )
                published_at = (soup.find("meta", property="article:published_time") or {}).get(
                    "content", ""
                )
                # fallbacks for the lead image
                if not image_url:
                    image_src = soup.find("link", rel="image_src")
                    if image_src and image_src.get("href"):
                        candidate = image_src["href"]
                        if candidate.startswith("http"):
                            image_url = candidate
                        else:
                            image_url = url + candidate
                if not image_url and content:
                    img_match = re.search(r"!\[[^\]]*\]\(([^)]+)\)", content)
                    if img_match:
                        image_url = img_match.group(1)
                if not image_url:
                    origin = f"{url.split('/')[0]}//{url.split('/')[2]}"
                    for img in soup.find_all("img"):
                        src = (img.get("src") or "").strip()
                        if src.startswith("//"):
                            src = "https:" + src
                        elif src.startswith("/"):
                            src = origin + src
                        if not src.startswith("http"):
                            continue
                        if any(bad in src.lower() for bad in ("data:", "1x1", "pixel", "sprite", "spacer", "favicon", "placeholder")):
                            continue
                        w = img.get("width")
                        h = img.get("height")
                        if w and h:
                            try:
                                if int(w) < 100 or int(h) < 60:
                                    continue
                            except ValueError:
                                pass
                        image_url = src
                        break
                if not image_url:
                    image_url = f"{origin}/favicon.ico"
    except Exception as e:
        logger.warning(f"scrape metadata extraction failed: {e}")
        logger.exception("scrape metadata traceback")

    if not content and not title:
        raise HTTPException(502, "scrape failed: could not read page")

    if not title:
        title = url

    # crude content summary (first meaningful sentences)
    summary = _auto_summary(content)

    return {
        "url": url,
        "title": title.strip()[:300],
        "content": content[:MAX_MARKDOWN],
        "image_url": image_url,
        "author": author[:200],
        "published_at": published_at,
        "summary": summary,
    }


@app.post("/rss")
async def rss(req: RSSRequest):
    import feedparser

    try:
        parsed = feedparser.parse(req.feed_url)
        if getattr(parsed, "bozo", False) and not parsed.entries:
            raise HTTPException(502, f"could not parse feed: {parsed.bozo_exception}")
        entries = []
        for e in parsed.entries[:20]:
            image = ""
            for link in e.get("links", []):
                if link.get("rel") in ("enclosure", "thumbnail") and link.get("type", "").startswith("image"):
                    image = link.get("href", "")
                    break
            if not image and e.get("media_content"):
                image = e["media_content"][0].get("url", "")
            if not image and e.get("media_thumbnail"):
                image = e["media_thumbnail"][0].get("url", "")
            if not image:
                m = re.search(r'<img[^>]+src=["\']([^"\']+)', e.get("summary", "") or "")
                if m:
                    image = m.group(1)
            published = e.get("published") or e.get("updated") or ""
            if e.get("published_parsed"):
                published = time.strftime("%Y-%m-%dT%H:%M:%SZ", e["published_parsed"])
            entries.append(
                {
                    "title": (e.get("title") or "").strip(),
                    "link": e.get("link", ""),
                    "summary": (e.get("summary") or e.get("description") or "")[:1000],
                    "content": (e.get("content", [{}])[0].get("value") or "")[:3000]
                    if e.get("content")
                    else "",
                    "image_url": image,
                    "author": (e.get("author") or ""),
                    "published_at": published,
                }
            )
        return {"feed_title": (parsed.feed.get("title") or ""), "entries": entries}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(502, f"rss parse failed: {e}")


def _clean_ddg(markdown: str) -> str:
    """Resolve DuckDuckGo redirect links back to the real target URL."""
    return re.sub(
        r"https://duckduckgo\.com/l/\?uddg=([^)&]+)",
        lambda m: m.group(1).replace("%3A", ":").replace("%2F", "/"),
        markdown,
    )


def _auto_summary(text: str, max_sentences: int = 2) -> str:
    if not text:
        return ""
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.lower().startswith(
            ("title:", "url source:", "published time:", "warning:", "markdown content:")
        ):
            continue
        lines.append(stripped)
    text = " ".join(lines)
    text = re.sub(r"\s+", " ", text)
    sentences = re.split(r"(?<=[.!?])\s+", text)
    picked = []
    for s in sentences:
        s = s.strip()
        if not s or len(s) < 20 or any(k in s.lower() for k in ("jina.ai", "you.com", "©", "javascript", "cookie", "read more")):
            continue
        picked.append(s)
        if len(picked) >= max_sentences:
            break
    return " ".join(picked)[:600]
