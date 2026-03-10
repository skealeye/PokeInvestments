"""Main application window."""
import logging
from datetime import datetime

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QTabWidget,
    QSplitter, QSizePolicy, QMessageBox
)
from PyQt6.QtCore import Qt, QThreadPool
from PyQt6.QtGui import QAction

from app.data import repository
from app.data.models import Product
from app.ui.dashboard_widget import DashboardWidget
from app.ui.portfolio_widget import PortfolioWidget
from app.ui.chart_widget import ChartWidget
from app.ui.inventory_dialog import InventoryDialog
from app.ui.status_bar import StatusBar
from app.workers.refresh_worker import RefreshWorker
from app.workers.forecast_worker import ForecastWorker
from app.settings import DEFAULT_REFRESH_INTERVAL_HOURS

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Pokemon Investments Tracker")
        self.resize(1400, 800)
        self._refresh_worker: RefreshWorker | None = None
        self._forecast_worker: ForecastWorker | None = None
        self._thread_pool = QThreadPool.globalInstance()

        self._build_ui()
        self._check_auto_refresh()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Tabs: Dashboard / Portfolio
        self.tabs = QTabWidget()
        root_layout.addWidget(self.tabs)

        # Dashboard tab (left: table, right: chart)
        dashboard_tab = QWidget()
        dash_layout = QVBoxLayout(dashboard_tab)
        dash_layout.setContentsMargins(0, 0, 0, 0)
        dash_layout.setSpacing(0)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)

        self.dashboard = DashboardWidget()
        self.dashboard.product_selected.connect(self._on_product_selected)
        self.dashboard.manage_holdings_requested.connect(self._open_inventory_dialog)
        self.splitter.addWidget(self.dashboard)

        self.chart = ChartWidget()
        self.chart.setMinimumWidth(350)
        self.splitter.addWidget(self.chart)
        self.splitter.setSizes([800, 550])

        dash_layout.addWidget(self.splitter)
        self.tabs.addTab(dashboard_tab, "Dashboard")

        # Portfolio tab
        self.portfolio = PortfolioWidget()
        self.portfolio.manage_product_requested.connect(self._open_inventory_dialog_by_id)
        self.tabs.addTab(self.portfolio, "Portfolio")

        # Status bar
        self.status_bar_widget = StatusBar()
        self.status_bar_widget.refresh_requested.connect(self._start_refresh)
        self.setStatusBar(None)
        root_layout.addWidget(self.status_bar_widget)

        # Load last refresh time
        last_refresh = repository.get_setting("last_refresh_time", "Never")
        self.status_bar_widget.set_last_updated(last_refresh)

        # Menu
        self._build_menu()

    def _build_menu(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("File")
        refresh_action = QAction("Refresh Prices", self)
        refresh_action.setShortcut("Ctrl+R")
        refresh_action.triggered.connect(self._start_refresh)
        file_menu.addAction(refresh_action)
        file_menu.addSeparator()
        quit_action = QAction("Quit", self)
        quit_action.setShortcut("Ctrl+Q")
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        view_menu = menubar.addMenu("View")
        dash_action = QAction("Dashboard", self)
        dash_action.triggered.connect(lambda: self.tabs.setCurrentIndex(0))
        view_menu.addAction(dash_action)
        portfolio_action = QAction("Portfolio", self)
        portfolio_action.triggered.connect(lambda: self.tabs.setCurrentIndex(1))
        view_menu.addAction(portfolio_action)

        help_menu = menubar.addMenu("Help")
        about_action = QAction("About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _check_auto_refresh(self):
        last_str = repository.get_setting("last_refresh_time")
        if not last_str or last_str == "Never":
            return
        try:
            last_dt = datetime.strptime(last_str, "%Y-%m-%d %H:%M:%S")
            hours_elapsed = (datetime.now() - last_dt).total_seconds() / 3600
            if hours_elapsed >= DEFAULT_REFRESH_INTERVAL_HOURS:
                logger.info("Auto-refreshing (data is stale)")
                self._start_refresh()
        except Exception as e:
            logger.warning(f"Could not parse last_refresh_time: {e}")

    def _start_refresh(self):
        if self._refresh_worker is not None:
            return  # Already running

        products = repository.get_all_products()
        self._refresh_worker = RefreshWorker(products)
        self._refresh_worker.signals.product_updated.connect(self._on_product_price_updated)
        self._refresh_worker.signals.progress.connect(self.status_bar_widget.set_progress)
        self._refresh_worker.signals.finished.connect(self._on_refresh_finished)
        self._refresh_worker.signals.error.connect(self._on_refresh_error)

        self.status_bar_widget.set_refreshing(True)
        self._thread_pool.start(self._refresh_worker)

    def _on_product_price_updated(self, product_id: int, market_price: float):
        self.dashboard.on_price_updated(product_id, market_price)

    def _on_refresh_finished(self, timestamp: str):
        self._refresh_worker = None
        self.status_bar_widget.set_refreshing(False)
        self.status_bar_widget.set_last_updated(timestamp)

        # Refresh portfolio totals
        self.portfolio.refresh()

        # Start forecast computation
        self._start_forecast()

    def _on_refresh_error(self, msg: str):
        self._refresh_worker = None
        self.status_bar_widget.set_refreshing(False)
        logger.error(f"Refresh error: {msg}")

    def _start_forecast(self):
        products = repository.get_all_products()
        self._forecast_worker = ForecastWorker(products)
        self._forecast_worker.signals.finished.connect(self._on_forecast_finished)
        self._forecast_worker.signals.error.connect(lambda e: logger.warning(f"Forecast error: {e}"))
        self._thread_pool.start(self._forecast_worker)

    def _on_forecast_finished(self):
        self._forecast_worker = None
        self.dashboard.on_forecasts_updated()
        self.portfolio.refresh()
        # Reload chart if product is loaded
        if self.chart._product:
            self.chart.load_product(self.chart._product)

    def _on_product_selected(self, product: Product):
        self.chart.load_product(product)

    def _open_inventory_dialog(self, product: Product):
        dialog = InventoryDialog(product, self)
        dialog.inventory_changed.connect(self._on_inventory_changed)
        dialog.exec()

    def _open_inventory_dialog_by_id(self, product_id: int):
        products = repository.get_all_products()
        product = next((p for p in products if p.id == product_id), None)
        if product:
            self._open_inventory_dialog(product)

    def _on_inventory_changed(self):
        self.dashboard.on_inventory_changed()
        self.portfolio.refresh()

    def _show_about(self):
        QMessageBox.about(
            self, "About Pokemon Investments Tracker",
            "<h3>Pokemon Investments Tracker</h3>"
            "<p>Track Scarlet &amp; Violet sealed product prices and portfolio value.</p>"
            "<p>Price data from <b>TCGCSV.com</b> (TCGPlayer mirror).</p>"
            "<p><i>Predictions are speculative. Not financial advice.</i></p>"
            "<br><p style='color: #8b949e; font-size: 10px;'>Pokemon and all related names are "
            "trademarks of Nintendo/Creatures Inc./GAME FREAK Inc.</p>"
        )

    def closeEvent(self, event):
        if self._refresh_worker:
            self._refresh_worker.cancel()
        super().closeEvent(event)
