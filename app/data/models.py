"""Dataclass models representing the domain objects."""
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional


@dataclass
class Set:
    id: int
    code: str
    name: str
    release_date: date
    series: str = "Scarlet & Violet"


@dataclass
class Product:
    id: int
    set_id: int
    product_type: str          # 'booster_box' | 'etb' | 'pc_etb'
    name: str
    tcgcsv_group_id: Optional[str] = None
    tcgcsv_product_id: Optional[str] = None
    msrp: Optional[float] = None
    # Joined fields (not DB columns)
    set_name: Optional[str] = None
    set_code: Optional[str] = None
    release_date: Optional[date] = None


@dataclass
class PriceRecord:
    id: Optional[int]
    product_id: int
    source: str
    market_price: Optional[float]
    low_price: Optional[float]
    mid_price: Optional[float]
    high_price: Optional[float]
    recorded_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Forecast:
    id: Optional[int]
    product_id: int
    model_name: str            # 'linear' | 'prophet'
    horizon_years: int         # 1 | 2 | 5 | 10
    predicted_price: float
    lower_bound: Optional[float]
    upper_bound: Optional[float]
    confidence: Optional[float]
    computed_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class InventoryEntry:
    id: Optional[int]
    product_id: int
    quantity: int
    purchase_price: float      # price paid per unit
    purchase_date: date
    notes: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class PortfolioRow:
    """Computed portfolio data for a single product."""
    product_id: int
    product_name: str
    set_name: str
    product_type: str
    quantity: int
    avg_purchase_price: float
    cost_basis: float
    market_price: Optional[float]
    current_value: Optional[float]
    unrealized_gain: Optional[float]
    unrealized_gain_pct: Optional[float]
    forecast_1y: Optional[float] = None
    forecast_2y: Optional[float] = None
    forecast_5y: Optional[float] = None
    forecast_10y: Optional[float] = None
