"""SQLAlchemy database setup and DDL."""
from sqlalchemy import (
    create_engine, MetaData, Table, Column,
    Integer, Text, Float, Date, DateTime, Index,
    UniqueConstraint, ForeignKey, text
)
from app.settings import DB_PATH

metadata = MetaData()

sets_table = Table(
    "sets", metadata,
    Column("id", Integer, primary_key=True),
    Column("code", Text, nullable=False, unique=True),
    Column("name", Text, nullable=False),
    Column("release_date", Date, nullable=False),
    Column("series", Text, nullable=False, server_default="Scarlet & Violet"),
)

products_table = Table(
    "products", metadata,
    Column("id", Integer, primary_key=True),
    Column("set_id", Integer, ForeignKey("sets.id"), nullable=False),
    Column("product_type", Text, nullable=False),
    Column("name", Text, nullable=False),
    Column("tcgcsv_group_id", Text),
    Column("tcgcsv_product_id", Text),
    Column("msrp", Float),
    UniqueConstraint("set_id", "product_type", name="uq_product_set_type"),
)

price_records_table = Table(
    "price_records", metadata,
    Column("id", Integer, primary_key=True),
    Column("product_id", Integer, ForeignKey("products.id"), nullable=False),
    Column("source", Text, nullable=False),
    Column("market_price", Float),
    Column("low_price", Float),
    Column("mid_price", Float),
    Column("high_price", Float),
    Column("recorded_at", DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")),
    Index("idx_price_records_product_date", "product_id", "recorded_at"),
)

forecasts_table = Table(
    "forecasts", metadata,
    Column("id", Integer, primary_key=True),
    Column("product_id", Integer, ForeignKey("products.id"), nullable=False),
    Column("model_name", Text, nullable=False),
    Column("horizon_years", Integer, nullable=False),
    Column("predicted_price", Float, nullable=False),
    Column("lower_bound", Float),
    Column("upper_bound", Float),
    Column("confidence", Float),
    Column("computed_at", DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")),
    UniqueConstraint("product_id", "model_name", "horizon_years", name="uq_forecast"),
)

inventory_table = Table(
    "inventory", metadata,
    Column("id", Integer, primary_key=True),
    Column("product_id", Integer, ForeignKey("products.id"), nullable=False),
    Column("quantity", Integer, nullable=False, server_default="1"),
    Column("purchase_price", Float, nullable=False),
    Column("purchase_date", Date, nullable=False),
    Column("notes", Text),
    Column("created_at", DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")),
    Index("idx_inventory_product", "product_id"),
)

settings_table = Table(
    "settings", metadata,
    Column("key", Text, primary_key=True),
    Column("value", Text, nullable=False),
)

_engine = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
    return _engine


def create_all_tables():
    engine = get_engine()
    metadata.create_all(engine)
    return engine
