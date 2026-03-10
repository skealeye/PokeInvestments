"""Tests for forecasting models."""
import os
import sys
import tempfile
from pathlib import Path
from datetime import datetime, timedelta

os.environ["APPDATA"] = tempfile.mkdtemp()
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import numpy as np
import pandas as pd

from app.forecasting.linear_model import LinearForecastModel
from app.forecasting.base_model import ForecastResult


def make_history(n_days: int = 60, start_price: float = 140.0,
                 drift: float = 0.02) -> pd.DataFrame:
    """Generate synthetic price history."""
    start = datetime.utcnow() - timedelta(days=n_days)
    rows = []
    price = start_price
    for i in range(n_days):
        price *= (1 + drift / 365 + np.random.normal(0, 0.005))
        rows.append({"ds": start + timedelta(days=i), "y": price})
    return pd.DataFrame(rows)


def test_linear_model_fits_and_predicts():
    df = make_history(60)
    model = LinearForecastModel(msrp=144.0)
    model.fit(df)

    result = model.predict(1)
    assert isinstance(result, ForecastResult)
    assert result.horizon_years == 1
    assert result.predicted_price > 0
    assert result.model_name == "linear"


def test_linear_model_all_horizons():
    df = make_history(90)
    model = LinearForecastModel()
    model.fit(df)

    results = model.predict_all([1, 2, 5, 10])
    assert len(results) == 4
    for r in results:
        assert r.predicted_price > 0
        assert r.lower_bound is not None
        assert r.upper_bound is not None
        assert r.lower_bound < r.predicted_price < r.upper_bound


def test_linear_confidence_decreases_with_horizon():
    df = make_history(90)
    model = LinearForecastModel()
    model.fit(df)

    r1 = model.predict(1)
    r10 = model.predict(10)
    assert r1.confidence >= r10.confidence


def test_linear_bands_widen_with_horizon():
    df = make_history(90)
    model = LinearForecastModel(msrp=144.0)
    model.fit(df)

    r1 = model.predict(1)
    r10 = model.predict(10)
    band_1 = r1.upper_bound - r1.lower_bound
    band_10 = r10.upper_bound - r10.lower_bound
    assert band_10 > band_1


def test_linear_model_not_fitted_raises():
    model = LinearForecastModel()
    with pytest.raises(RuntimeError):
        model.predict(1)


def test_prophet_fallback_when_unavailable():
    """ProphetForecastModel should fall back to linear if Prophet not installed."""
    from app.forecasting.prophet_model import ProphetForecastModel, PROPHET_AVAILABLE
    df = make_history(60)
    model = ProphetForecastModel(msrp=144.0)
    model.fit(df)
    result = model.predict(5)
    assert result.predicted_price > 0
    # Model name will be 'prophet' if installed else 'linear'
    assert result.model_name in ("prophet", "linear")


def test_forecast_service_insufficient_data():
    """ForecastService should return empty list with <30 days of history."""
    import os
    os.environ["APPDATA"] = tempfile.mkdtemp()
    from app.data.database import create_all_tables
    from app.data.seed_data import upsert_all
    create_all_tables()
    upsert_all()

    from app.forecasting.forecast_service import ForecastService
    from app.data import repository

    products = repository.get_all_products()
    # No price history inserted, so should return empty
    service = ForecastService()
    results = service.compute_forecasts(products[0])
    assert results == []
