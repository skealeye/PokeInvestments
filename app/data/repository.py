"""All database read/write operations."""
from datetime import datetime, date, timedelta
from typing import Optional
from sqlalchemy import select, insert, update, delete, func, and_, text

from app.data.database import (
    get_engine, sets_table, products_table, price_records_table,
    forecasts_table, inventory_table, settings_table
)
from app.data.models import (
    Set, Product, PriceRecord, Forecast, InventoryEntry, PortfolioRow
)


def get_all_sets() -> list[Set]:
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(select(sets_table).order_by(sets_table.c.release_date)).fetchall()
    return [Set(id=r.id, code=r.code, name=r.name,
                release_date=r.release_date, series=r.series) for r in rows]


def get_all_products() -> list[Product]:
    """Return all products joined with set info."""
    engine = get_engine()
    with engine.connect() as conn:
        stmt = (
            select(
                products_table,
                sets_table.c.name.label("set_name"),
                sets_table.c.code.label("set_code"),
                sets_table.c.release_date.label("release_date"),
            )
            .join(sets_table, products_table.c.set_id == sets_table.c.id)
            .order_by(sets_table.c.release_date, products_table.c.product_type)
        )
        rows = conn.execute(stmt).fetchall()
    return [
        Product(
            id=r.id, set_id=r.set_id, product_type=r.product_type,
            name=r.name, tcgcsv_group_id=r.tcgcsv_group_id,
            tcgcsv_product_id=r.tcgcsv_product_id, msrp=r.msrp,
            set_name=r.set_name, set_code=r.set_code, release_date=r.release_date
        )
        for r in rows
    ]


def get_latest_price(product_id: int) -> Optional[PriceRecord]:
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(
            select(price_records_table)
            .where(price_records_table.c.product_id == product_id)
            .order_by(price_records_table.c.recorded_at.desc())
            .limit(1)
        ).fetchone()
    if not row:
        return None
    return PriceRecord(
        id=row.id, product_id=row.product_id, source=row.source,
        market_price=row.market_price, low_price=row.low_price,
        mid_price=row.mid_price, high_price=row.high_price,
        recorded_at=row.recorded_at
    )


def get_latest_prices_all() -> dict[int, PriceRecord]:
    """Return the latest price record for each product (efficient single query)."""
    engine = get_engine()
    with engine.connect() as conn:
        # Subquery: max recorded_at per product
        subq = (
            select(
                price_records_table.c.product_id,
                func.max(price_records_table.c.recorded_at).label("max_ts")
            )
            .group_by(price_records_table.c.product_id)
            .subquery()
        )
        stmt = (
            select(price_records_table)
            .join(
                subq,
                and_(
                    price_records_table.c.product_id == subq.c.product_id,
                    price_records_table.c.recorded_at == subq.c.max_ts
                )
            )
        )
        rows = conn.execute(stmt).fetchall()
    return {
        row.product_id: PriceRecord(
            id=row.id, product_id=row.product_id, source=row.source,
            market_price=row.market_price, low_price=row.low_price,
            mid_price=row.mid_price, high_price=row.high_price,
            recorded_at=row.recorded_at
        )
        for row in rows
    }


def get_price_history(product_id: int, days: int = 730) -> list[PriceRecord]:
    engine = get_engine()
    cutoff = datetime.utcnow() - timedelta(days=days)
    with engine.connect() as conn:
        rows = conn.execute(
            select(price_records_table)
            .where(
                and_(
                    price_records_table.c.product_id == product_id,
                    price_records_table.c.recorded_at >= cutoff
                )
            )
            .order_by(price_records_table.c.recorded_at)
        ).fetchall()
    return [
        PriceRecord(
            id=r.id, product_id=r.product_id, source=r.source,
            market_price=r.market_price, low_price=r.low_price,
            mid_price=r.mid_price, high_price=r.high_price,
            recorded_at=r.recorded_at
        )
        for r in rows
    ]


def insert_price_record(record: PriceRecord) -> int:
    engine = get_engine()
    with engine.begin() as conn:
        result = conn.execute(
            insert(price_records_table).values(
                product_id=record.product_id,
                source=record.source,
                market_price=record.market_price,
                low_price=record.low_price,
                mid_price=record.mid_price,
                high_price=record.high_price,
                recorded_at=record.recorded_at or datetime.utcnow()
            )
        )
    return result.inserted_primary_key[0]


def get_forecasts_for_product(product_id: int) -> dict[int, Forecast]:
    """Return forecasts keyed by horizon_years."""
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            select(forecasts_table)
            .where(forecasts_table.c.product_id == product_id)
            .order_by(forecasts_table.c.computed_at.desc())
        ).fetchall()
    result = {}
    for row in rows:
        if row.horizon_years not in result:
            result[row.horizon_years] = Forecast(
                id=row.id, product_id=row.product_id,
                model_name=row.model_name, horizon_years=row.horizon_years,
                predicted_price=row.predicted_price,
                lower_bound=row.lower_bound, upper_bound=row.upper_bound,
                confidence=row.confidence, computed_at=row.computed_at
            )
    return result


def get_all_latest_forecasts() -> dict[tuple[int, int], Forecast]:
    """Return latest forecast per (product_id, horizon_years)."""
    engine = get_engine()
    with engine.connect() as conn:
        subq = (
            select(
                forecasts_table.c.product_id,
                forecasts_table.c.horizon_years,
                func.max(forecasts_table.c.computed_at).label("max_ts")
            )
            .group_by(forecasts_table.c.product_id, forecasts_table.c.horizon_years)
            .subquery()
        )
        stmt = select(forecasts_table).join(
            subq,
            and_(
                forecasts_table.c.product_id == subq.c.product_id,
                forecasts_table.c.horizon_years == subq.c.horizon_years,
                forecasts_table.c.computed_at == subq.c.max_ts
            )
        )
        rows = conn.execute(stmt).fetchall()
    return {
        (row.product_id, row.horizon_years): Forecast(
            id=row.id, product_id=row.product_id,
            model_name=row.model_name, horizon_years=row.horizon_years,
            predicted_price=row.predicted_price,
            lower_bound=row.lower_bound, upper_bound=row.upper_bound,
            confidence=row.confidence, computed_at=row.computed_at
        )
        for row in rows
    }


def upsert_forecast(forecast: Forecast):
    engine = get_engine()
    with engine.begin() as conn:
        existing = conn.execute(
            select(forecasts_table.c.id).where(
                and_(
                    forecasts_table.c.product_id == forecast.product_id,
                    forecasts_table.c.model_name == forecast.model_name,
                    forecasts_table.c.horizon_years == forecast.horizon_years
                )
            )
        ).fetchone()
        vals = dict(
            predicted_price=forecast.predicted_price,
            lower_bound=forecast.lower_bound,
            upper_bound=forecast.upper_bound,
            confidence=forecast.confidence,
            computed_at=forecast.computed_at or datetime.utcnow()
        )
        if existing:
            conn.execute(forecasts_table.update().where(
                forecasts_table.c.id == existing.id).values(**vals))
        else:
            conn.execute(forecasts_table.insert().values(
                product_id=forecast.product_id,
                model_name=forecast.model_name,
                horizon_years=forecast.horizon_years,
                **vals
            ))


def get_inventory_for_product(product_id: int) -> list[InventoryEntry]:
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            select(inventory_table)
            .where(inventory_table.c.product_id == product_id)
            .order_by(inventory_table.c.purchase_date)
        ).fetchall()
    return [
        InventoryEntry(
            id=r.id, product_id=r.product_id, quantity=r.quantity,
            purchase_price=r.purchase_price, purchase_date=r.purchase_date,
            notes=r.notes, created_at=r.created_at
        )
        for r in rows
    ]


def get_all_inventory() -> list[InventoryEntry]:
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            select(inventory_table).order_by(inventory_table.c.product_id)
        ).fetchall()
    return [
        InventoryEntry(
            id=r.id, product_id=r.product_id, quantity=r.quantity,
            purchase_price=r.purchase_price, purchase_date=r.purchase_date,
            notes=r.notes, created_at=r.created_at
        )
        for r in rows
    ]


def add_inventory_entry(entry: InventoryEntry) -> int:
    engine = get_engine()
    with engine.begin() as conn:
        result = conn.execute(
            insert(inventory_table).values(
                product_id=entry.product_id,
                quantity=entry.quantity,
                purchase_price=entry.purchase_price,
                purchase_date=entry.purchase_date,
                notes=entry.notes,
                created_at=entry.created_at or datetime.utcnow()
            )
        )
    return result.inserted_primary_key[0]


def update_inventory_entry(entry: InventoryEntry):
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(
            inventory_table.update()
            .where(inventory_table.c.id == entry.id)
            .values(
                quantity=entry.quantity,
                purchase_price=entry.purchase_price,
                purchase_date=entry.purchase_date,
                notes=entry.notes
            )
        )


def delete_inventory_entry(entry_id: int):
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(
            inventory_table.delete().where(inventory_table.c.id == entry_id)
        )


def get_owned_quantities() -> dict[int, int]:
    """Return total owned quantity per product_id."""
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            select(
                inventory_table.c.product_id,
                func.sum(inventory_table.c.quantity).label("total_qty")
            ).group_by(inventory_table.c.product_id)
        ).fetchall()
    return {row.product_id: row.total_qty for row in rows}


def get_setting(key: str, default: str = None) -> Optional[str]:
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(
            select(settings_table.c.value).where(settings_table.c.key == key)
        ).fetchone()
    return row.value if row else default


def set_setting(key: str, value: str):
    engine = get_engine()
    with engine.begin() as conn:
        existing = conn.execute(
            select(settings_table.c.key).where(settings_table.c.key == key)
        ).fetchone()
        if existing:
            conn.execute(settings_table.update().where(
                settings_table.c.key == key).values(value=value))
        else:
            conn.execute(settings_table.insert().values(key=key, value=value))


def get_portfolio_rows() -> list[PortfolioRow]:
    """Compute portfolio rows by joining inventory, products, prices, forecasts."""
    engine = get_engine()
    with engine.connect() as conn:
        # Aggregated inventory per product
        inv_q = (
            select(
                inventory_table.c.product_id,
                func.sum(inventory_table.c.quantity).label("total_qty"),
                (
                    func.sum(inventory_table.c.quantity * inventory_table.c.purchase_price) /
                    func.sum(inventory_table.c.quantity)
                ).label("avg_price"),
                func.sum(inventory_table.c.quantity * inventory_table.c.purchase_price).label("cost_basis")
            )
            .group_by(inventory_table.c.product_id)
            .subquery()
        )

        # Latest price per product
        price_subq = (
            select(
                price_records_table.c.product_id,
                func.max(price_records_table.c.recorded_at).label("max_ts")
            )
            .group_by(price_records_table.c.product_id)
            .subquery()
        )
        latest_price_q = (
            select(price_records_table.c.product_id, price_records_table.c.market_price)
            .join(price_subq, and_(
                price_records_table.c.product_id == price_subq.c.product_id,
                price_records_table.c.recorded_at == price_subq.c.max_ts
            ))
            .subquery()
        )

        stmt = (
            select(
                products_table.c.id.label("product_id"),
                products_table.c.name.label("product_name"),
                products_table.c.product_type,
                sets_table.c.name.label("set_name"),
                inv_q.c.total_qty,
                inv_q.c.avg_price,
                inv_q.c.cost_basis,
                latest_price_q.c.market_price,
            )
            .join(sets_table, products_table.c.set_id == sets_table.c.id)
            .join(inv_q, products_table.c.id == inv_q.c.product_id)
            .outerjoin(latest_price_q, products_table.c.id == latest_price_q.c.product_id)
            .order_by(sets_table.c.release_date, products_table.c.product_type)
        )
        rows = conn.execute(stmt).fetchall()

    # Get forecasts
    all_forecasts = get_all_latest_forecasts()

    result = []
    for r in rows:
        mp = r.market_price
        cv = r.total_qty * mp if mp is not None else None
        gain = (cv - r.cost_basis) if cv is not None else None
        gain_pct = ((cv / r.cost_basis - 1) * 100) if (cv is not None and r.cost_basis) else None

        def fc(horizon):
            f = all_forecasts.get((r.product_id, horizon))
            return f.predicted_price * r.total_qty if f else None

        result.append(PortfolioRow(
            product_id=r.product_id,
            product_name=r.product_name,
            set_name=r.set_name,
            product_type=r.product_type,
            quantity=r.total_qty,
            avg_purchase_price=r.avg_price,
            cost_basis=r.cost_basis,
            market_price=mp,
            current_value=cv,
            unrealized_gain=gain,
            unrealized_gain_pct=gain_pct,
            forecast_1y=fc(1),
            forecast_2y=fc(2),
            forecast_5y=fc(5),
            forecast_10y=fc(10),
        ))
    return result
