"""Ridge regression forecast on log-prices."""
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from typing import Optional

from app.forecasting.base_model import ForecastModel, ForecastResult


class LinearForecastModel(ForecastModel):
    """
    Ridge regression on log(price) with features:
    - days_since_start
    - month_sin / month_cos (seasonality)
    - rolling_30d_avg, rolling_90d_avg
    - msrp_ratio (if msrp available)
    Confidence bands from time-series cross-validation residuals.
    """

    def __init__(self, msrp: Optional[float] = None):
        self.msrp = msrp
        self._model = Ridge(alpha=1.0)
        self._scaler = StandardScaler()
        self._last_day: Optional[int] = None
        self._last_log_price: Optional[float] = None
        self._cv_rmse: float = 0.0
        self._fitted = False

    @property
    def name(self) -> str:
        return "linear"

    def _build_features(self, df: pd.DataFrame) -> np.ndarray:
        days = (df["ds"] - df["ds"].iloc[0]).dt.days.values
        months = df["ds"].dt.month.values
        month_sin = np.sin(2 * np.pi * months / 12)
        month_cos = np.cos(2 * np.pi * months / 12)

        prices = df["y"].values
        roll30 = pd.Series(prices).rolling(30, min_periods=1).mean().values
        roll90 = pd.Series(prices).rolling(90, min_periods=1).mean().values

        features = [days, month_sin, month_cos, roll30, roll90]
        if self.msrp and self.msrp > 0:
            msrp_ratio = prices / self.msrp
            features.append(msrp_ratio)

        return np.column_stack(features)

    def fit(self, history: pd.DataFrame) -> None:
        df = history.sort_values("ds").reset_index(drop=True)

        self._start_date = df["ds"].iloc[0]
        self._last_day = (df["ds"].iloc[-1] - self._start_date).days
        self._last_row = df.iloc[-1:]
        self._sparse = len(df) < 10

        if self._sparse:
            # Not enough points for reliable regression — store current price
            # and derive a growth rate from MSRP ratio only when we have
            # enough elapsed days to make the annualisation meaningful.
            self._current_price = float(df["y"].iloc[-1])
            days_elapsed = max(self._last_day, 0)
            if self.msrp and self.msrp > 0 and self._current_price > 0 and days_elapsed >= 30:
                ratio = self._current_price / self.msrp
                # Annualised growth implied by MSRP → current over elapsed time
                self._annual_growth = max(0.0, ratio ** (365.0 / days_elapsed) - 1)
                self._annual_growth = min(self._annual_growth, 0.40)  # cap 40%/yr
            else:
                # Default: sealed Pokemon historically appreciates ~8%/yr on average
                self._annual_growth = 0.08
            self._fitted = True
            return

        X = self._build_features(df)
        y = np.log(np.clip(df["y"].values, 0.01, None))

        X_scaled = self._scaler.fit_transform(X)
        self._model.fit(X_scaled, y)
        self._fitted = True

        # Cross-validation residuals for confidence band
        self._cv_rmse = self._compute_cv_rmse(df, X, y)

    def _compute_cv_rmse(self, df: pd.DataFrame, X: np.ndarray, y: np.ndarray) -> float:
        n = len(df)
        if n < 10:
            return 0.15  # default 15% band for insufficient data
        split = max(5, n // 3)
        X_train = self._scaler.transform(X[:split])
        model_cv = Ridge(alpha=1.0)
        model_cv.fit(X_train, y[:split])
        preds = model_cv.predict(self._scaler.transform(X[split:]))
        residuals = y[split:] - preds
        return float(np.std(residuals))

    def predict(self, horizon_years: int) -> ForecastResult:
        if not self._fitted:
            raise RuntimeError("Model not fitted yet")

        if self._sparse:
            # Simple compound growth from current price
            predicted = self._current_price * ((1 + self._annual_growth) ** horizon_years)
            # Wide bands for sparse data — uncertainty grows with horizon
            band_pct = 0.20 + horizon_years * 0.10
            lower = predicted * (1 - band_pct)
            upper = predicted * (1 + band_pct)
            confidence = max(0.3, 0.60 - horizon_years * 0.05)
            return ForecastResult(
                horizon_years=horizon_years,
                predicted_price=round(predicted, 2),
                lower_bound=round(lower, 2),
                upper_bound=round(upper, 2),
                confidence=round(confidence, 3),
                model_name=self.name,
            )

        future_day = self._last_day + int(horizon_years * 365.25)
        future_date = self._start_date + pd.Timedelta(days=future_day)

        last_price = self._last_row["y"].values[0]
        month = future_date.month
        roll30 = last_price
        roll90 = last_price

        feat = [future_day,
                np.sin(2 * np.pi * month / 12),
                np.cos(2 * np.pi * month / 12),
                roll30, roll90]
        if self.msrp and self.msrp > 0:
            feat.append(last_price / self.msrp)

        X_pred = self._scaler.transform([feat])
        log_pred = float(self._model.predict(X_pred)[0])
        predicted = float(np.exp(log_pred))

        # Confidence widens with horizon
        horizon_factor = 1.0 + (horizon_years - 1) * 0.3
        band = float(np.exp(self._cv_rmse * horizon_factor))
        lower = predicted / band
        upper = predicted * band
        confidence = max(0.3, 0.95 - horizon_years * 0.08)

        return ForecastResult(
            horizon_years=horizon_years,
            predicted_price=round(predicted, 2),
            lower_bound=round(lower, 2),
            upper_bound=round(upper, 2),
            confidence=round(confidence, 3),
            model_name=self.name,
        )
