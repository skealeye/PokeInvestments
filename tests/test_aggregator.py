"""Tests for the price aggregator."""
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

os.environ["APPDATA"] = tempfile.mkdtemp()
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from app.data.database import create_all_tables
from app.data.seed_data import upsert_all
from app.data import repository
from app.api.aggregator import PriceAggregator, _type_keywords


@pytest.fixture(autouse=True)
def setup_db():
    create_all_tables()
    upsert_all()


def test_type_keywords():
    assert "booster box" in _type_keywords("booster_box")
    assert "elite trainer" in _type_keywords("etb")
    assert "pokemon center" in _type_keywords("pc_etb")


def test_aggregator_tcgcsv_match():
    """Test that TCGCSV client result is parsed and returned."""
    products = repository.get_all_products()
    product = next(p for p in products if p.set_code == "sv1" and p.product_type == "booster_box")

    mock_price_data = [{
        "productId": product.tcgcsv_product_id,
        "marketPrice": 155.00,
        "lowPrice": 140.00,
        "midPrice": 150.00,
        "highPrice": 165.00,
        "subTypeName": "Booster Box",
    }]

    aggregator = PriceAggregator()
    with patch.object(aggregator._tcgcsv, 'get_group_prices', return_value=mock_price_data):
        record = aggregator.fetch_price(product)

    assert record is not None
    assert record.source == "tcgcsv"
    assert record.market_price == 155.00
    assert record.product_id == product.id


def test_aggregator_fallback_on_empty():
    """Test fallback when TCGCSV returns no prices."""
    products = repository.get_all_products()
    product = products[0]

    aggregator = PriceAggregator()
    with patch.object(aggregator._tcgcsv, 'get_group_prices', return_value=[]):
        with patch.object(aggregator._price_tracker, 'get_sealed_price', return_value=None):
            with patch.object(aggregator._pokewallet, 'get_sealed_price', return_value=None):
                record = aggregator.fetch_price(product)

    assert record is None


def test_aggregator_cache():
    """Verify group cache prevents redundant requests."""
    products = repository.get_all_products()
    # Get two products from same set
    sv1_products = [p for p in products if p.set_code == "sv1"]

    mock_prices = [{"productId": p.tcgcsv_product_id, "marketPrice": 100.0,
                    "lowPrice": 90.0, "midPrice": 95.0, "highPrice": 110.0}
                   for p in sv1_products if p.tcgcsv_product_id]

    call_count = 0
    def mock_get_group(group_id):
        nonlocal call_count
        call_count += 1
        return mock_prices

    aggregator = PriceAggregator()
    with patch.object(aggregator._tcgcsv, 'get_group_prices', side_effect=mock_get_group):
        for p in sv1_products[:2]:
            aggregator.fetch_price(p)

    # Should only call API once for the same group
    assert call_count == 1
