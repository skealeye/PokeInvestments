"""Background worker: fetch all product prices."""
import logging
from datetime import datetime

from PyQt6.QtCore import QRunnable, QObject, pyqtSignal, pyqtSlot

from app.api.aggregator import PriceAggregator
from app.data import repository
from app.data.models import Product

logger = logging.getLogger(__name__)


class RefreshSignals(QObject):
    product_updated = pyqtSignal(int, float)    # product_id, market_price
    progress = pyqtSignal(int, int)             # current, total
    finished = pyqtSignal(str)                  # timestamp string
    error = pyqtSignal(str)


class RefreshWorker(QRunnable):
    def __init__(self, products: list[Product]):
        super().__init__()
        self.products = products
        self.signals = RefreshSignals()
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    @pyqtSlot()
    def run(self):
        aggregator = PriceAggregator()
        total = len(self.products)
        updated = 0

        try:
            for i, product in enumerate(self.products):
                if self._cancelled:
                    break
                self.signals.progress.emit(i + 1, total)
                try:
                    record = aggregator.fetch_price(product)
                    if record:
                        repository.insert_price_record(record)
                        if record.market_price:
                            self.signals.product_updated.emit(product.id, record.market_price)
                            updated += 1
                except Exception as e:
                    logger.warning(f"Failed to fetch {product.name}: {e}")
        except Exception as e:
            self.signals.error.emit(str(e))
        finally:
            aggregator.close()
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            repository.set_setting("last_refresh_time", ts)
            self.signals.finished.emit(ts)
            logger.info(f"Refresh complete: {updated}/{total} products updated")
