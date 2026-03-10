"""Model selection and forecast orchestration."""
import logging
from datetime import datetime
import pandas as pd

from app.forecasting.linear_model import LinearForecastModel
from app.forecasting.prophet_model import ProphetForecastModel
from app.data.models import Product, PriceRecord, Forecast
from app.data import repository
from app.settings import FORECAST_HORIZONS, MIN_HISTORY_DAYS_FOR_FORECAST

logger = logging.getLogger(__name__)


class ForecastService:
    def compute_forecasts(self, product: Product) -> list[Forecast]:
        """Fetch history, pick model, run, return Forecast objects."""
        history = repository.get_price_history(product.id, days=730)
        if not history:
            logger.debug(f"No history for {product.name}")
            return []

        df = _to_dataframe(history)
        n_days = (df["ds"].iloc[-1] - df["ds"].iloc[0]).days

        if n_days < MIN_HISTORY_DAYS_FOR_FORECAST:
            logger.debug(f"Insufficient history ({n_days}d) for {product.name}")
            return []

        results = []
        for horizon in FORECAST_HORIZONS:
            try:
                if horizon <= 2:
                    model = LinearForecastModel(msrp=product.msrp)
                else:
                    model = ProphetForecastModel(msrp=product.msrp)
                model.fit(df)
                fr = model.predict(horizon)
                results.append(Forecast(
                    id=None,
                    product_id=product.id,
                    model_name=fr.model_name,
                    horizon_years=fr.horizon_years,
                    predicted_price=fr.predicted_price,
                    lower_bound=fr.lower_bound,
                    upper_bound=fr.upper_bound,
                    confidence=fr.confidence,
                    computed_at=datetime.utcnow(),
                ))
            except Exception as e:
                logger.warning(f"Forecast {horizon}Y failed for {product.name}: {e}")

        return results


def _to_dataframe(history: list[PriceRecord]) -> pd.DataFrame:
    rows = []
    for r in history:
        price = r.market_price or r.mid_price or r.low_price
        if price and price > 0:
            rows.append({"ds": pd.Timestamp(r.recorded_at), "y": price})
    df = pd.DataFrame(rows).drop_duplicates(subset=["ds"]).sort_values("ds")
    return df.reset_index(drop=True)
