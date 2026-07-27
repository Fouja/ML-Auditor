"""
Kijiji scraper service for marketplace integration.
Uses requests + BeautifulSoup for HTTP-based scraping.
"""

import logging
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

KIJII_BASE_URL = "https://www.kijiji.ca"

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

        Args:
            query: Search query
            location: Location filter (e.g., "toronto", "montreal")
            category: Category filter
            min_price: Minimum price
            max_price: Maximum price
            sort_by: Sort order (date, price)

        Returns:
            List of listings
        """
        try:
            params = {"query": query}
            if location:
                params["location"] = location
            if min_price:
                params["price__gte"] = str(int(min_price))
            if max_price:
                params["price__lte"] = str(int(max_price))
            if sort_by == "price":
                params["sort"] = "priceAsc"

            url = (
                f"{KIJII_BASE_URL}/b-{query.replace(' ', '-')}/k0l0?{urlencode(params)}"
            )
            logger.info(f"Scraping Kijiji: {url}")

            resp = self.session.get(url, timeout=15)
            resp.raise_for_status()

            return self._parse_search_results(resp.text)
        except requests.RequestException as e:
            logger.error(f"Kijiji search request failed: {e}")
            return []
        except Exception as e:
            logger.error(f"Kijiji search error: {e}")
            return []

    def _parse_search_results(self, html: str) -> List[Dict[str, Any]]:
        """Parse Kijiji search results page HTML."""
        soup = BeautifulSoup(html, "html.parser")
        listings = []

        # Kijiji uses various class patterns for listing cards
        cards = soup.select('[class*="sc-"] a[href*="/b-"]') or soup.select(
            'a[href*="/b-"]'
        )

        if not cards:
            # Fallback: try to find listing links
            cards = soup.find_all("a", href=re.compile(r"/b-.*-k\d+l\d+"))

        for card in cards[:30]:
            try:
                listing = self._parse_listing_card(card)
                if listing and listing.get("title"):
                    listings.append(listing)
            except Exception as e:
                logger.debug(f"Failed to parse listing card: {e}")
                continue

        return listings

    def _parse_listing_card(self, card) -> Dict[str, Any]:
        """Parse a single listing card element."""
        title = ""
        price = None
        location = ""
        url = ""
        image_url = ""
        listing_id = ""

        # Get title
        title_el = (
            card.select_one('[class*="title"]')
            or card.select_one("h3")
            or card.select_one("h2")
        )
        if title_el:
            title = title_el.get_text(strip=True)
        elif card.get_text(strip=True):
            title = card.get_text(strip=True)[:100]

        # Get URL
        href = card.get("href", "")
        if href:
            if href.startswith("/"):
                url = f"{KIJII_BASE_URL}{href}"
            else:
                url = href

        # Extract listing ID from URL
        id_match = re.search(r"-k(\d+)l(\d+)", url)
        if id_match:
            listing_id = f"{id_match.group(1)}_{id_match.group(2)}"

        # Get price
        price_el = card.select_one('[class*="price"]') or card.select_one(
            '[data-testid*="price"]'
        )
        if price_el:
            price_text = price_el.get_text(strip=True)
            price_match = re.search(r"\$?([\d,]+(?:\.\d{2})?)", price_text)
            if price_match:
                price = float(price_match.group(1).replace(",", ""))

        # Get location
        location_el = card.select_one('[class*="location"]') or card.select_one(
            '[class*="date"]'
        )
        if location_el:
            location = location_el.get_text(strip=True)

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
