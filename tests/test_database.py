"""Tests for database setup and seed data."""
import os
import sys
import tempfile
from pathlib import Path
from datetime import date

# Point to temp DB for tests
os.environ["APPDATA"] = tempfile.mkdtemp()
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from app.data.database import create_all_tables, get_engine, sets_table, products_table
from app.data.seed_data import upsert_all, SV_SETS, PRODUCT_MATRIX
from app.data import repository


@pytest.fixture(autouse=True)
def setup_db():
    create_all_tables()
    upsert_all()
    yield


def test_sets_seeded():
    sets = repository.get_all_sets()
    codes = [s.code for s in sets]
    assert "sv1" in codes
    assert "sv8pt5" in codes
    assert len(sets) == len(SV_SETS)


def test_products_seeded():
    products = repository.get_all_products()
    assert len(products) > 0
    # sv1 has 3 products
    sv1_products = [p for p in products if p.set_code == "sv1"]
    assert len(sv1_products) == 3


def test_product_types():
    products = repository.get_all_products()
    types = set(p.product_type for p in products)
    assert "booster_box" in types
    assert "etb" in types
    assert "pc_etb" in types


def test_sv2_has_no_pc_etb():
    products = repository.get_all_products()
    sv2_types = [p.product_type for p in products if p.set_code == "sv2"]
    assert "pc_etb" not in sv2_types


def test_price_record_insert_and_retrieve():
    from app.data.models import PriceRecord
    from datetime import datetime
    products = repository.get_all_products()
    p = products[0]
    record = PriceRecord(
        id=None, product_id=p.id, source="tcgcsv",
        market_price=150.00, low_price=140.00,
        mid_price=148.00, high_price=160.00,
        recorded_at=datetime.utcnow()
    )
    repository.insert_price_record(record)
    latest = repository.get_latest_price(p.id)
    assert latest is not None
    assert latest.market_price == 150.00


def test_inventory_crud():
    from app.data.models import InventoryEntry
    products = repository.get_all_products()
    p = products[0]

    entry = InventoryEntry(
        id=None, product_id=p.id, quantity=3,
        purchase_price=145.00, purchase_date=date(2024, 1, 15),
        notes="Test purchase"
    )
    entry_id = repository.add_inventory_entry(entry)
    assert entry_id is not None

    entries = repository.get_inventory_for_product(p.id)
    assert len(entries) == 1
    assert entries[0].quantity == 3

    entries[0].quantity = 5
    repository.update_inventory_entry(entries[0])
    updated = repository.get_inventory_for_product(p.id)
    assert updated[0].quantity == 5

    repository.delete_inventory_entry(entries[0].id)
    deleted = repository.get_inventory_for_product(p.id)
    assert len(deleted) == 0


def test_settings():
    repository.set_setting("test_key", "test_value")
    val = repository.get_setting("test_key")
    assert val == "test_value"
    # Upsert
    repository.set_setting("test_key", "new_value")
    assert repository.get_setting("test_key") == "new_value"
    # Default
    assert repository.get_setting("nonexistent", "default") == "default"
