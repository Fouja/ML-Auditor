"""
Kijiji scraper service for marketplace integration.
Uses requests + BeautifulSoup for HTTP-based scraping.
"""

import concurrent.futures
import logging
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

KIJII_BASE_URL = "https://www.kijiji.ca"

SEARCH_TIMEOUT_SECONDS = 20

# Kijiji aggressively blocks scrapers (Cloudflare-style challenges) and DNS/TLS
# stalls can hang a plain requests call far beyond its timeout. Run each HTTP
# fetch in a short-lived worker thread and enforce a hard wall-clock deadline
# so search_listings can never block the caller indefinitely.
_search_executor = concurrent.futures.ThreadPoolExecutor(
    max_workers=4, thread_name_prefix="kijiji"
)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}


class KijijiScraperService:
    """
    Service for scraping Kijiji listings and messages.
    Uses HTTP requests to scrape kijiji.ca search results.
    """

    def __init__(self, user=None):
        self.user = user
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    def _do_get(self, url: str) -> "requests.Response":
        # Fresh session per request: Session objects are not thread-safe and
        # the module-level executor reuses threads across calls.
        session = requests.Session()
        session.headers.update(HEADERS)
        return session.get(url, timeout=(10, 10))

    def search_listings(
        self,
        query: str,
        location: Optional[str] = None,
        category: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        sort_by: str = "date",
    ) -> List[Dict[str, Any]]:
        """
        Search for listings on Kijiji via HTTP scraping.

        Kijiji's URL layout: ``https://www.kijiji.ca/b-<location>/<query-slug>/k0l0``.

        The previous implementation put the query in the *location* slot
        (``/b-iphone-13-pro/k0l0``), which made Kijiji interpret ``k0l0`` as
        the search term (title said "ads for k0l0") and ignore the user's
        real query. The fix is to use a real location slug (default
        "canada" for nationwide) and put the query in its proper slot.

        Args:
            query: Search query
            location: Location slug (e.g. "canada", "ontario", "toronto")
            category: Category slug (e.g. "cell-phones")
            min_price: Minimum price
            max_price: Maximum price
            sort_by: Sort order (date, price)
        """
        try:
            query_slug = re.sub(r"[^a-z0-9]+", "-", (query or "").lower()).strip("-")
            if not query_slug:
                return []
            loc_slug = (location or "canada").strip().lower() or "canada"
            if not loc_slug.startswith("ontario") and not loc_slug.startswith("canada") and not loc_slug.startswith("toronto") and not loc_slug.startswith("montreal") and not loc_slug.startswith("vancouver") and not loc_slug.startswith("calgary") and not loc_slug.startswith("alberta"):
                # Unknown custom location — fall back to nationwide so
                # users aren't greeted with 0 results when typping the
                # wrong slug.
                loc_slug = "canada"

            # Price filter goes in the URL path: /k0l0?price=200..2000
            url = f"{KIJII_BASE_URL}/b-{loc_slug}/{query_slug}/k0l0"
            qs = {}
            qs["sort"] = "dateDesc" if sort_by == "date" else "priceAsc"
            if min_price is not None and max_price is not None:
                qs["price"] = f"{int(min_price)}..{int(max_price)}"
            elif min_price is not None:
                qs["price"] = f"{int(min_price)}__"
            elif max_price is not None:
                qs["price"] = f"0..{int(max_price)}"
            if category:
                qs["sc"] = category

            full_url = f"{url}?{urlencode(qs)}"
            logger.info(f"Scraping Kijiji: {full_url}")

            future = _search_executor.submit(self._do_get, full_url)
            try:
                resp = future.result(timeout=SEARCH_TIMEOUT_SECONDS)
            except concurrent.futures.TimeoutError:
                logger.error(f"Kijiji search timed out after {SEARCH_TIMEOUT_SECONDS}s: {full_url}")
                return []
            resp.raise_for_status()

            return self._parse_search_results(resp.text)
        except requests.RequestException as e:
            logger.error(f"Kijiji search request failed: {e}")
            return []
        except Exception as e:
            logger.error(f"Kijiji search error: {e}")
            return []

    def _parse_search_results(self, html: str) -> List[Dict[str, Any]]:
        """Parse Kijiji search results page HTML.

        Kijiji renders listings as Next.js SSR with stable
        ``data-testid="listing-card"`` wrappers and inner ``data-testid``
        hooks for title/price/location/url. We rely on those instead of
        the brittle ``sc-*`` class names.
        """
        soup = BeautifulSoup(html, "html.parser")
        listings: List[Dict[str, Any]] = []

        cards = soup.select('[data-testid="listing-card"]')
        if not cards:
            # Legacy fallback for older markup
            cards = soup.select('[class*="sc-"] a[href*="/v-"]')

        seen_ids = set()
        for card in cards[:30]:
            try:
                listing = self._parse_listing_card(card)
                if listing and listing.get("title") and listing.get("id") not in seen_ids:
                    seen_ids.add(listing.get("id"))
                    listings.append(listing)
            except Exception as e:
                logger.debug(f"Failed to parse listing card: {e}")
                continue

        return listings

    def _parse_listing_card(self, card) -> Dict[str, Any]:
        """Parse a single ``data-testid="listing-card"`` element."""
        title = ""
        price: Optional[float] = None
        location = ""
        url = ""
        image_url = ""
        listing_id = ""

        # Listing ID — surface as data-listingid on the <section>
        listing_id = card.get("data-listingid", "") or ""

        # Title
        title_link = card.select_one('[data-testid="listing-link"]') or card.select_one(
            'a[href*="/v-"]'
        )
        if title_link:
            title = title_link.get_text(strip=True)
            href = title_link.get("href", "")
            if href:
                url = href if href.startswith("http") else f"{KIJII_BASE_URL}{href}"
            if not listing_id:
                m = re.search(r"/(\d+)(?:\?|$)", href or "")
                if m:
                    listing_id = m.group(1)
        else:
            title_el = card.select_one('[data-testid="listing-title"]') or card.select_one("h3") or card.select_one("h2")
            if title_el:
                title = title_el.get_text(strip=True)

        # Price
        price_el = card.select_one('[data-testid="listing-price"]')
        if price_el:
            price_text = price_el.get_text(strip=True)
            m = re.search(r"\$?\s*([\d,]+(?:\.\d{2})?)", price_text)
            if m:
                try:
                    price = float(m.group(1).replace(",", ""))
                except ValueError:
                    price = None

        # Location
        loc_el = card.select_one('[data-testid="listing-location"]')
        if loc_el:
            location = loc_el.get_text(strip=True)

        # Image
        img_el = card.select_one('[data-testid="listing-card-image"]')
        if img_el:
            image_url = img_el.get("src", "") or img_el.get("data-src", "")

        if not title:
            return {}
        return {
            "id": listing_id,
            "title": title,
            "price": price,
            "location": location,
            "url": url,
            "image_url": image_url,
        }


        # Get image
        img_el = card.select_one("img")
        if img_el:
            image_url = img_el.get("src", "") or img_el.get("data-src", "")

        return {
            "id": listing_id or title[:30].replace(" ", "_"),
            "title": title,
            "price": price,
            "location": location,
            "url": url,
            "image_url": image_url,
        }

    def get_listing_details(self, listing_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a listing.
        """
        try:
            # Try to fetch the listing page
            url = (
                listing_id
                if listing_id.startswith("http")
                else f"{KIJII_BASE_URL}/b/{listing_id}"
            )
            resp = self.session.get(url, timeout=15)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            title_el = soup.select_one("h1") or soup.select_one('[class*="title"]')
            title = title_el.get_text(strip=True) if title_el else ""

            price_el = soup.select_one('[class*="price"]')
            price = None
            if price_el:
                price_match = re.search(r"\$?([\d,]+)", price_el.get_text())
                if price_match:
                    price = float(price_match.group(1).replace(",", ""))

            description_el = soup.select_one(
                '[class*="description"]'
            ) or soup.select_one('[data-testid*="description"]')
            description = description_el.get_text(strip=True) if description_el else ""

            return {
                "id": listing_id,
                "title": title,
                "price": price,
                "description": description,
                "url": url,
            }
        except Exception as e:
            logger.error(f"Failed to get listing details: {e}")
            return {"id": listing_id, "error": str(e)}

    def get_messages(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get messages from Kijiji inbox.
        Requires authentication - returns empty if not logged in.
        """
        logger.info("Kijiji messages requires authentication. Not implemented.")
        return []

    def send_message(
        self,
        listing_id: str,
        recipient_id: str,
        message: str,
    ) -> bool:
        """
        Send a message on Kijiji.
        Requires authentication.
        """
        logger.info("Kijiji send message requires authentication. Not implemented.")
        return False

    def analyze_listing(self, listing: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze a listing for potential deals.
        """
        price = listing.get("price")
        title = listing.get("title", "").lower()

        is_good_deal = False
        estimated_value = 0
        confidence = 0

        if price is not None:
            # Basic heuristic: check for keywords suggesting good deals
            deal_keywords = [
                "free",
                "cheap",
                "must go",
                "urgent",
                "moving",
                "liquidation",
                "sale",
            ]
            if any(kw in title for kw in deal_keywords):
                is_good_deal = True
                confidence = 0.6
                estimated_value = price * 1.3

        return {
            "is_good_deal": is_good_deal,
            "estimated_value": estimated_value,
            "confidence": confidence,
            "recommendation": (
                "Good deal detected" if is_good_deal else "No strong deal signals found"
            ),
        }

    def analyze_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze a message for spam/negotiation.
        """
        content = message.get("content", "").lower()

        lowball_keywords = [
            "lowest",
            "best price",
            "final offer",
            "$50",
            "$100",
            "can you do less",
        ]
        is_lowball = any(kw in content for kw in lowball_keywords)

        spam_keywords = [
            "click here",
            "free money",
            "wire transfer",
            "western union",
            "send money",
        ]
        is_spam = any(kw in content for kw in spam_keywords)

        return {
            "is_spam": is_spam,
            "is_genuine": not is_spam,
            "is_lowball": is_lowball,
            "sentiment": "negative" if is_lowball else "neutral",
            "suggested_response": None,
        }
