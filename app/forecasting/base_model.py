"""Abstract base class for forecast models."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
import pandas as pd


@dataclass
class ForecastResult:
    horizon_years: int
    predicted_price: float
    lower_bound: Optional[float]
    upper_bound: Optional[float]
    confidence: Optional[float]
    model_name: str


class ForecastModel(ABC):
    """Abstract interface for price forecast models."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Short model identifier stored in DB."""
        ...

    @abstractmethod
    def fit(self, history: pd.DataFrame) -> None:
        """
        Fit the model to historical price data.
        history: DataFrame with columns ['ds' (datetime), 'y' (price)]
        """
        ...

    @abstractmethod
    def predict(self, horizon_years: int) -> ForecastResult:
        """Generate forecast for given horizon in years."""
        ...

    def predict_all(self, horizons: list[int]) -> list[ForecastResult]:
        return [self.predict(h) for h in horizons]
