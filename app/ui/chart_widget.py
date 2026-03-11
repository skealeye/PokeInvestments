"""PyQtGraph price history chart with forecast overlay."""
import logging
from datetime import datetime, timedelta
from typing import Optional

import numpy as np
import pyqtgraph as pg
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QCheckBox
)
from PyQt6.QtCore import Qt

from app.data.models import Product, PriceRecord, Forecast
from app.data import repository

logger = logging.getLogger(__name__)

# Chart colors
COLOR_MARKET = "#388bfd"
COLOR_BAND = (56, 139, 253, 40)      # semi-transparent blue fill
COLOR_MSRP = "#f0c040"
COLOR_COST = "#f85149"
COLOR_GAIN_FILL = (63, 185, 80, 30)
FORECAST_COLORS = {1: "#ff9944", 2: "#ffcc44", 5: "#cc44ff", 10: "#ff4488"}


def _dt_to_ts(dt) -> float:
    """Convert datetime to Unix timestamp."""
    if isinstance(dt, datetime):
        return dt.timestamp()
    return float(dt)


class ChartWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._product: Optional[Product] = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        # Header
        header = QHBoxLayout()
        self.title_label = QLabel("Select a product to view price history")
        self.title_label.setStyleSheet("font-size: 15px; font-weight: 700; color: #f0c040;")
        header.addWidget(self.title_label)
        header.addStretch()

        self.show_forecasts_cb = QCheckBox("Show Forecasts")
        self.show_forecasts_cb.setChecked(True)
        self.show_forecasts_cb.toggled.connect(self._toggle_forecasts)
        header.addWidget(self.show_forecasts_cb)

        self.show_bands_cb = QCheckBox("Show Bands")
        self.show_bands_cb.setChecked(True)
        self.show_bands_cb.toggled.connect(self._toggle_bands)
        header.addWidget(self.show_bands_cb)

        layout.addLayout(header)

        # PyQtGraph setup
        pg.setConfigOptions(antialias=True, background="#0d1117", foreground="#c9d1d9")

        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setLabel("left", "Price (USD)")
        self.plot_widget.setLabel("bottom", "Date")
        self.plot_widget.showGrid(x=True, y=True, alpha=0.2)
        self.plot_widget.setMouseEnabled(x=True, y=True)
        self.plot_widget.setMenuEnabled(False)

        # Date axis on X
        axis = pg.DateAxisItem(orientation="bottom")
        self.plot_widget.setAxisItems({"bottom": axis})

        self.legend = self.plot_widget.addLegend(offset=(10, 10))
        layout.addWidget(self.plot_widget)

        # Info bar
        self.info_label = QLabel("")
        self.info_label.setStyleSheet("color: #8b949e; font-size: 11px;")
        layout.addWidget(self.info_label)

        # Disclaimer
        disclaimer = QLabel(
            "Predictions are speculative estimates based on historical trends. "
            "Not financial advice. Past performance does not guarantee future results."
        )
        disclaimer.setStyleSheet("color: #484f58; font-size: 10px; font-style: italic;")
        disclaimer.setWordWrap(True)
        layout.addWidget(disclaimer)

        # Store plot items for toggling
        self._forecast_items = []
        self._band_items = []
        self._cost_items = []

    def load_product(self, product: Product):
        self._product = product
        self.title_label.setText(f"{product.name}")
        self._render()

    def _render(self):
        if not self._product:
            return
        p = self._product
        self.plot_widget.clear()
        self._forecast_items = []
        self._band_items = []
        self._cost_items = []

        history = repository.get_price_history(p.id, days=730)
        forecasts = repository.get_forecasts_for_product(p.id)
        inventory = repository.get_inventory_for_product(p.id)

        if not history:
            self.info_label.setText("No price history available yet. Click 'Refresh Now' to fetch prices.")
            return

        # Build x/y arrays
        xs = np.array([_dt_to_ts(r.recorded_at) for r in history])
        ys_market = np.array([r.market_price or r.mid_price or 0.0 for r in history])
        ys_low = np.array([r.low_price or ys_market[i] for i, r in enumerate(history)])
        ys_high = np.array([r.high_price or ys_market[i] for i, r in enumerate(history)])

        # Price band fill (low-high)
        band = pg.FillBetweenItem(
            pg.PlotDataItem(xs, ys_low),
            pg.PlotDataItem(xs, ys_high),
            brush=pg.mkBrush(*COLOR_BAND)
        )
        self.plot_widget.addItem(band)
        self._band_items.append(band)

        # Market price line
        market_curve = self.plot_widget.plot(
            xs, ys_market,
            pen=pg.mkPen(COLOR_MARKET, width=2),
            name="Market Price"
        )

        # MSRP reference line
        if p.msrp:
            msrp_line = pg.InfiniteLine(
                pos=p.msrp, angle=0,
                pen=pg.mkPen(COLOR_MSRP, width=1, style=Qt.PenStyle.DashLine)
            )
            self.plot_widget.addItem(msrp_line)
            msrp_label = pg.TextItem(f"MSRP ${p.msrp:.0f}", color=COLOR_MSRP, anchor=(0, 1))
            msrp_label.setPos(xs[0], p.msrp)
            self.plot_widget.addItem(msrp_label)

        # Cost basis line (if owned)
        if inventory:
            total_qty = sum(e.quantity for e in inventory)
            avg_cost = sum(e.quantity * e.purchase_price for e in inventory) / total_qty
            cost_line = pg.InfiniteLine(
                pos=avg_cost, angle=0,
                pen=pg.mkPen(COLOR_COST, width=1.5, style=Qt.PenStyle.DashLine),
                label=f"Avg Cost ${avg_cost:.2f}",
                labelOpts={"color": COLOR_COST, "position": 0.95}
            )
            self.plot_widget.addItem(cost_line)
            self._cost_items.append(cost_line)

            # Gain zone shading from cost_basis to current market
            current = ys_market[-1] if len(ys_market) else avg_cost
            if current > avg_cost:
                gain_fill = pg.FillBetweenItem(
                    pg.PlotDataItem(xs, np.full_like(xs, avg_cost)),
                    pg.PlotDataItem(xs, np.minimum(ys_market, current)),
                    brush=pg.mkBrush(*COLOR_GAIN_FILL)
                )
                self.plot_widget.addItem(gain_fill)
                self._cost_items.append(gain_fill)

        # Forecast lines (extend from last data point)
        last_ts = xs[-1]
        last_price = ys_market[-1]

        for horizon, forecast in forecasts.items():
            color = FORECAST_COLORS.get(horizon, "#ffffff")
            future_ts = last_ts + horizon * 365.25 * 86400
            fc_xs = np.array([last_ts, future_ts])
            fc_ys = np.array([last_price, forecast.predicted_price])

            fc_curve = self.plot_widget.plot(
                fc_xs, fc_ys,
                pen=pg.mkPen(color, width=1.5, style=Qt.PenStyle.DotLine),
                name=f"{horizon}Y Forecast"
            )
            self._forecast_items.append(fc_curve)

            # Confidence band
            if forecast.lower_bound and forecast.upper_bound:
                fc_lo = pg.PlotDataItem(fc_xs, np.array([last_price, forecast.lower_bound]))
                fc_hi = pg.PlotDataItem(fc_xs, np.array([last_price, forecast.upper_bound]))
                band_color = pg.mkColor(color)
                band_color.setAlpha(20)
                fc_band = pg.FillBetweenItem(fc_lo, fc_hi,
                                             brush=pg.mkBrush(band_color))
                self.plot_widget.addItem(fc_band)
                self._band_items.append(fc_band)

        # Update info
        latest_price = ys_market[-1] if len(ys_market) else None
        info_parts = [f"{len(history)} data points"]
        if latest_price:
            info_parts.append(f"Latest: ${latest_price:.2f}")
        if forecasts:
            info_parts.append(f"Forecasts: {len(forecasts)} horizons")
        self.info_label.setText(" | ".join(info_parts))

    def _toggle_forecasts(self, checked: bool):
        for item in self._forecast_items:
            item.setVisible(checked)

    def _toggle_bands(self, checked: bool):
        for item in self._band_items:
            item.setVisible(checked)

    def clear(self):
        self._product = None
        self.plot_widget.clear()
        self.title_label.setText("Select a product to view price history")
        self.info_label.setText("")
