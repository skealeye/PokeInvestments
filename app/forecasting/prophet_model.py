"""Facebook Prophet wrapper with graceful ImportError fallback."""
import logging
from typing import Optional
import pandas as pd

from app.forecasting.base_model import ForecastModel, ForecastResult

logger = logging.getLogger(__name__)

try:
    from prophet import Prophet
    PROPHET_AVAILABLE = True
except ImportError:
    PROPHET_AVAILABLE = False
    logger.info("Prophet not installed; long-range forecasts will use linear model")


class ProphetForecastModel(ForecastModel):
    """
    Facebook Prophet for long-range forecasting (5-10 year).
    Falls back to LinearForecastModel if Prophet is not installed.
    """

    def __init__(self, msrp: Optional[float] = None):
        self.msrp = msrp
        self._model = None
        self._start_date = None
        self._fitted = False

    @property
    def name(self) -> str:
        return "prophet" if PROPHET_AVAILABLE else "linear"

    @property
    def available(self) -> bool:
        return PROPHET_AVAILABLE

    def fit(self, history: pd.DataFrame) -> None:
        if not PROPHET_AVAILABLE:
            # Delegate to linear
            from app.forecasting.linear_model import LinearForecastModel
            self._fallback = LinearForecastModel(msrp=self.msrp)
            self._fallback.fit(history)
            self._fitted = True
            return

        df = history.sort_values("ds").reset_index(drop=True)
        self._start_date = df["ds"].iloc[0]
        self._last_date = df["ds"].iloc[-1]

        m = Prophet(
            growth="linear",
            yearly_seasonality=True,
            weekly_seasonality=False,
            daily_seasonality=False,
            changepoint_prior_scale=0.3,
            interval_width=0.80,
        )
        m.fit(df[["ds", "y"]])
        self._model = m
        self._fitted = True
        self._fallback = None

    def predict(self, horizon_years: int) -> ForecastResult:
        if not self._fitted:
            raise RuntimeError("Model not fitted yet")

        if not PROPHET_AVAILABLE or self._model is None:
            return self._fallback.predict(horizon_years)

        periods = int(horizon_years * 365)
        future = self._model.make_future_dataframe(periods=periods, freq="D")
        forecast = self._model.predict(future)
        last_row = forecast.iloc[-1]

        predicted = max(0.01, float(last_row["yhat"]))
        lower = max(0.01, float(last_row["yhat_lower"]))
        upper = max(0.01, float(last_row["yhat_upper"]))
        confidence = max(0.3, 0.90 - horizon_years * 0.05)

        return ForecastResult(
            horizon_years=horizon_years,
            predicted_price=round(predicted, 2),
            lower_bound=round(lower, 2),
            upper_bound=round(upper, 2),
            confidence=round(confidence, 3),
            model_name="prophet",
        )
