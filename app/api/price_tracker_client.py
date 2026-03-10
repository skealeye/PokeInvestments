"""Fallback price source: pokemonpricetracker.com"""
import logging
from typing import Optional
from app.api.base_client import BaseClient

logger = logging.getLogger(__name__)

PRICE_TRACKER_BASE = "https://www.pokemonpricetracker.com"


class PriceTrackerClient(BaseClient):
    def __init__(self):
        super().__init__(PRICE_TRACKER_BASE)

    def get_sealed_price(self, set_name: str, product_type: str) -> Optional[dict]:
        """
        Attempt to retrieve price data from pokemonpricetracker.com.
        This is a best-effort scraper fallback.
        """
        try:
            # The site has no public JSON API; this is a placeholder for
            # any endpoint that may be discoverable. Return None to trigger
            # next fallback in the aggregator chain.
            logger.debug(f"PriceTracker fallback called for {set_name} / {product_type}")
            return None
        except Exception as e:
            logger.warning(f"PriceTracker failed: {e}")
            return None
