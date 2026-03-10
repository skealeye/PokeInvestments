"""TCGCSV.com adapter - primary price source.

TCGCSV mirrors TCGPlayer pricing data, no auth required.
Endpoint: GET /tcgplayer/{categoryId}/{groupId}/prices
Returns array of price objects per product.
"""
import logging
from typing import Optional
from app.api.base_client import BaseClient
from app.settings import TCGCSV_BASE_URL, TCGCSV_POKEMON_CATEGORY

logger = logging.getLogger(__name__)


class TCGCSVClient(BaseClient):
    def __init__(self):
        super().__init__(TCGCSV_BASE_URL)

    def get_group_prices(self, group_id: str) -> list[dict]:
        """Fetch all product prices for a TCGPlayer group."""
        path = f"/tcgplayer/{TCGCSV_POKEMON_CATEGORY}/{group_id}/prices"
        try:
            data = self.get(path)
            if isinstance(data, list):
                return data
            # Some responses wrap in {"results": [...]}
            return data.get("results", [])
        except Exception as e:
            logger.warning(f"TCGCSV group {group_id} failed: {e}")
            return []

    def get_product_price(self, group_id: str, product_id: str) -> Optional[dict]:
        """Return price dict for a specific product_id within a group."""
        prices = self.get_group_prices(group_id)
        for item in prices:
            pid = str(item.get("productId", ""))
            if pid == str(product_id):
                return item
        return None

    def get_groups(self) -> list[dict]:
        """List all groups (sets) in the Pokemon category."""
        try:
            data = self.get(f"/tcgplayer/{TCGCSV_POKEMON_CATEGORY}/groups")
            if isinstance(data, list):
                return data
            return data.get("results", [])
        except Exception as e:
            logger.warning(f"TCGCSV groups list failed: {e}")
            return []

    def extract_price_data(self, price_obj: dict) -> dict:
        """Normalise a TCGCSV price object into standard fields."""
        # TCGCSV returns: {productId, lowPrice, midPrice, highPrice, marketPrice, directLowPrice, subTypeName}
        return {
            "market_price": price_obj.get("marketPrice"),
            "low_price": price_obj.get("lowPrice"),
            "mid_price": price_obj.get("midPrice"),
            "high_price": price_obj.get("highPrice"),
        }
