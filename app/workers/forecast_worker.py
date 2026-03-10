"""Background worker: compute forecasts for all products."""
import logging

from PyQt6.QtCore import QRunnable, QObject, pyqtSignal, pyqtSlot

from app.forecasting.forecast_service import ForecastService
from app.data import repository
from app.data.models import Product

logger = logging.getLogger(__name__)


class ForecastSignals(QObject):
    product_done = pyqtSignal(int)   # product_id
    finished = pyqtSignal()
    error = pyqtSignal(str)


class ForecastWorker(QRunnable):
    def __init__(self, products: list[Product]):
        super().__init__()
        self.products = products
        self.signals = ForecastSignals()

    @pyqtSlot()
    def run(self):
        service = ForecastService()
        try:
            for product in self.products:
                try:
                    forecasts = service.compute_forecasts(product)
                    for f in forecasts:
                        repository.upsert_forecast(f)
                    if forecasts:
                        self.signals.product_done.emit(product.id)
                except Exception as e:
                    logger.warning(f"Forecast failed for {product.name}: {e}")
        except Exception as e:
            self.signals.error.emit(str(e))
        finally:
            self.signals.finished.emit()
