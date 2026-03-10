"""Priority chain aggregator: tries sources in order, returns first successful PriceRecord."""
import logging
from datetime import datetime
from typing import Optional

from app.api.tcgcsv_client import TCGCSVClient
from app.api.price_tracker_client import PriceTrackerClient
from app.api.pokewallet_client import PokeWalletClient
from app.data.models import PriceRecord, Product

logger = logging.getLogger(__name__)


class PriceAggregator:
    def __init__(self):
        self._tcgcsv = TCGCSVClient()
        self._price_tracker = PriceTrackerClient()
        self._pokewallet = PokeWalletClient()
        # Cache group prices to avoid refetching same group per product
        self._group_cache: dict[str, list[dict]] = {}

    def fetch_price(self, product: Product) -> Optional[PriceRecord]:
        """Try TCGCSV → PriceTracker → PokeWallet, return first success."""

        # --- Source 1: TCGCSV ---
        record = self._try_tcgcsv(product)
        if record:
            return record

        # --- Source 2: PriceTracker (fallback) ---
        record = self._try_price_tracker(product)
        if record:
            return record

        # --- Source 3: PokeWallet (fallback 2) ---
        record = self._try_pokewallet(product)
        if record:
            return record

        logger.warning(f"All sources failed for product {product.id}: {product.name}")
        return None

    def _try_tcgcsv(self, product: Product) -> Optional[PriceRecord]:
        if not product.tcgcsv_group_id:
            return None
        try:
            group_id = product.tcgcsv_group_id
            if group_id not in self._group_cache:
                self._group_cache[group_id] = self._tcgcsv.get_group_prices(group_id)

            prices = self._group_cache[group_id]
            if not prices:
                return None

            # Find matching product by product_id or by name matching
            price_obj = None
            if product.tcgcsv_product_id:
                for item in prices:
                    if str(item.get("productId", "")) == str(product.tcgcsv_product_id):
                        price_obj = item
                        break

            # Fallback: match by product type keywords in subTypeName
            if price_obj is None:
                keywords = _type_keywords(product.product_type)
                for item in prices:
                    sub = (item.get("subTypeName") or "").lower()
                    name = (item.get("productName") or "").lower()
                    if any(kw in sub or kw in name for kw in keywords):
                        price_obj = item
                        break

            if price_obj is None:
                return None

            data = self._tcgcsv.extract_price_data(price_obj)
            if data.get("market_price") is None and data.get("mid_price") is None:
                return None

            return PriceRecord(
                id=None,
                product_id=product.id,
                source="tcgcsv",
                market_price=data.get("market_price"),
                low_price=data.get("low_price"),
                mid_price=data.get("mid_price"),
                high_price=data.get("high_price"),
                recorded_at=datetime.utcnow(),
            )
        except Exception as e:
            logger.warning(f"TCGCSV failed for {product.name}: {e}")
            return None

    def _try_price_tracker(self, product: Product) -> Optional[PriceRecord]:
        try:
            data = self._price_tracker.get_sealed_price(
                product.set_name or product.name, product.product_type
            )
            if not data:
                return None
            return PriceRecord(
                id=None, product_id=product.id, source="price_tracker",
                market_price=data.get("market_price"),
                low_price=data.get("low_price"),
                mid_price=data.get("mid_price"),
                high_price=data.get("high_price"),
                recorded_at=datetime.utcnow(),
            )
        except Exception as e:
            logger.warning(f"PriceTracker failed for {product.name}: {e}")
            return None

    def _try_pokewallet(self, product: Product) -> Optional[PriceRecord]:
        try:
            data = self._pokewallet.get_sealed_price(product.name)
            if not data:
                return None
            return PriceRecord(
                id=None, product_id=product.id, source="pokewallet",
                market_price=data.get("market_price"),
                low_price=data.get("low_price"),
                mid_price=data.get("mid_price"),
                high_price=data.get("high_price"),
                recorded_at=datetime.utcnow(),
            )
        except Exception as e:
            logger.warning(f"PokeWallet failed for {product.name}: {e}")
            return None

    def clear_cache(self):
        self._group_cache.clear()

    def close(self):
        self._tcgcsv.close()
        self._price_tracker.close()
        self._pokewallet.close()


def _type_keywords(product_type: str) -> list[str]:
    mapping = {
        "booster_box": ["booster box", "boosterbox", "booster_box"],
        "etb": ["elite trainer", "etb"],
        "pc_etb": ["pokemon center", "pc etb", "center etb"],
    }
    return mapping.get(product_type, [product_type])
