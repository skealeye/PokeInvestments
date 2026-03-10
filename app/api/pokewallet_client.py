"""Fallback price source: pokewallet.io"""
import logging
from typing import Optional
from app.api.base_client import BaseClient

logger = logging.getLogger(__name__)

POKEWALLET_BASE = "https://pokewallet.io"


class PokeWalletClient(BaseClient):
    def __init__(self):
        super().__init__(POKEWALLET_BASE)

    def get_sealed_price(self, product_name: str) -> Optional[dict]:
        """
        Attempt to retrieve price data from pokewallet.io.
        Placeholder fallback — returns None if unavailable.
        """
        try:
            logger.debug(f"PokeWallet fallback called for {product_name}")
            return None
        except Exception as e:
            logger.warning(f"PokeWallet failed: {e}")
            return None
