"""Portfolio tab: summary cards + holdings table + portfolio chart."""
import csv
from typing import Optional

import numpy as np
import pyqtgraph as pg
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QPushButton, QFileDialog, QMessageBox, QSplitter, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont

from app.data.models import PortfolioRow
from app.data import repository

FORECAST_COLORS = {1: "#ff9944", 2: "#ffcc44", 5: "#cc44ff", 10: "#ff4488"}


def _fmt_money(v: Optional[float]) -> str:
    return f"${v:,.2f}" if v is not None else "—"


def _fmt_pct(v: Optional[float]) -> str:
    if v is None:
        return "—"
    return f"+{v:.1f}%" if v >= 0 else f"{v:.1f}%"


class SummaryCard(QFrame):
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self.setMinimumWidth(140)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)

        self.title_lbl = QLabel(title)
        self.title_lbl.setObjectName("cardTitle")
        layout.addWidget(self.title_lbl)

        self.value_lbl = QLabel("—")
        self.value_lbl.setObjectName("cardValue")
        self.value_lbl.setStyleSheet("font-size: 20px; font-weight: 700; color: #f0c040;")
        layout.addWidget(self.value_lbl)

        self.sub_lbl = QLabel("")
        self.sub_lbl.setStyleSheet("color: #8b949e; font-size: 11px;")
        layout.addWidget(self.sub_lbl)

    def set_value(self, text: str, color: str = "#f0c040"):
        self.value_lbl.setText(text)
        self.value_lbl.setStyleSheet(f"font-size: 20px; font-weight: 700; color: {color};")

    def set_sub(self, text: str, color: str = "#8b949e"):
        self.sub_lbl.setText(text)
        self.sub_lbl.setStyleSheet(f"color: {color}; font-size: 11px;")


class PortfolioWidget(QWidget):
    manage_product_requested = pyqtSignal(int)  # product_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        # --- Summary cards row ---
        cards_row = QHBoxLayout()
        cards_row.setSpacing(8)

        self.card_invested = SummaryCard("TOTAL INVESTED")
        self.card_value = SummaryCard("CURRENT VALUE")
        self.card_gain = SummaryCard("UNREALIZED GAIN")
        self.card_1y = SummaryCard("1Y PROJECTED")
        self.card_2y = SummaryCard("2Y PROJECTED")
        self.card_5y = SummaryCard("5Y PROJECTED")
        self.card_10y = SummaryCard("10Y PROJECTED")

        for card in (self.card_invested, self.card_value, self.card_gain,
                     self.card_1y, self.card_2y, self.card_5y, self.card_10y):
            card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            cards_row.addWidget(card)

        main_layout.addLayout(cards_row)

        # --- Splitter: table + chart ---
        splitter = QSplitter(Qt.Orientation.Vertical)

        # Holdings table
        table_container = QWidget()
        tc_layout = QVBoxLayout(table_container)
        tc_layout.setContentsMargins(0, 0, 0, 0)

        th_row = QHBoxLayout()
        th_row.addWidget(QLabel("Holdings"))
        th_row.addStretch()
        export_btn = QPushButton("Export CSV")
        export_btn.clicked.connect(self._export_csv)
        export_btn.setFixedWidth(90)
        th_row.addWidget(export_btn)
        tc_layout.addLayout(th_row)

        cols = ["Product", "Set", "Type", "Qty", "Avg Cost",
                "Mkt Price", "Curr Value", "Gain $", "Gain %",
                "1Y Value", "2Y Value", "5Y Value", "10Y Value"]
        self.table = QTableWidget(0, len(cols))
        self.table.setHorizontalHeaderLabels(cols)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        self.table.verticalHeader().setVisible(False)
        tc_layout.addWidget(self.table)
        splitter.addWidget(table_container)

        # Portfolio chart
        chart_container = QWidget()
        cc_layout = QVBoxLayout(chart_container)
        cc_layout.setContentsMargins(0, 0, 0, 0)
        cc_layout.addWidget(QLabel("Portfolio Value Over Time"))

        pg.setConfigOptions(antialias=True, background="#0d1117", foreground="#c9d1d9")
        self.chart = pg.PlotWidget()
        self.chart.setLabel("left", "Portfolio Value (USD)")
        self.chart.setLabel("bottom", "Date")
        self.chart.showGrid(x=True, y=True, alpha=0.2)
        axis = pg.DateAxisItem(orientation="bottom")
        self.chart.setAxisItems({"bottom": axis})
        self.chart.addLegend(offset=(10, 10))
        cc_layout.addWidget(self.chart)

        disclaimer = QLabel(
            "Projected values are speculative. Not financial advice."
        )
        disclaimer.setStyleSheet("color: #484f58; font-size: 10px; font-style: italic;")
        cc_layout.addWidget(disclaimer)
        splitter.addWidget(chart_container)

        splitter.setSizes([300, 250])
        main_layout.addWidget(splitter)

    def refresh(self):
        rows = repository.get_portfolio_rows()
        self._populate_cards(rows)
        self._populate_table(rows)
        self._render_chart(rows)

    def _populate_cards(self, rows: list[PortfolioRow]):
        total_invested = sum(r.cost_basis for r in rows)
        total_value = sum(r.current_value for r in rows if r.current_value is not None)
        total_gain = total_value - total_invested if total_value else None
        gain_pct = (total_gain / total_invested * 100) if (total_gain is not None and total_invested) else None

        self.card_invested.set_value(_fmt_money(total_invested))
        self.card_value.set_value(_fmt_money(total_value or None))

        if total_gain is not None:
            color = "#3fb950" if total_gain >= 0 else "#f85149"
            self.card_gain.set_value(_fmt_money(total_gain), color)
            self.card_gain.set_sub(_fmt_pct(gain_pct), color)
        else:
            self.card_gain.set_value("—")

        for card, attr, horizon in [
            (self.card_1y, "forecast_1y", 1),
            (self.card_2y, "forecast_2y", 2),
            (self.card_5y, "forecast_5y", 5),
            (self.card_10y, "forecast_10y", 10),
        ]:
            proj_total = sum(getattr(r, attr) for r in rows if getattr(r, attr) is not None)
            proj_total = proj_total if proj_total > 0 else None
            proj_gain = (proj_total - total_invested) if proj_total else None
            proj_gain_pct = (proj_gain / total_invested * 100) if (proj_gain and total_invested) else None
            color = FORECAST_COLORS.get(horizon, "#f0c040")
            card.set_value(_fmt_money(proj_total), color)
            if proj_gain_pct is not None:
                card.set_sub(_fmt_pct(proj_gain_pct), color)

    def _populate_table(self, rows: list[PortfolioRow]):
        self.table.setRowCount(0)
        for row in rows:
            r = self.table.rowCount()
            self.table.insertRow(r)

            gain = row.unrealized_gain
            gain_color = QColor("#3fb950") if (gain or 0) >= 0 else QColor("#f85149")

            def item(text, color=None):
                i = QTableWidgetItem(str(text))
                i.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                if color:
                    i.setForeground(color)
                return i

            self.table.setItem(r, 0, QTableWidgetItem(row.product_name))
            self.table.setItem(r, 1, QTableWidgetItem(row.set_name))
            self.table.setItem(r, 2, QTableWidgetItem(row.product_type.replace("_", " ").title()))
            self.table.setItem(r, 3, item(str(row.quantity)))
            self.table.setItem(r, 4, item(_fmt_money(row.avg_purchase_price)))
            self.table.setItem(r, 5, item(_fmt_money(row.market_price)))
            self.table.setItem(r, 6, item(_fmt_money(row.current_value)))
            self.table.setItem(r, 7, item(_fmt_money(gain), gain_color))
            self.table.setItem(r, 8, item(_fmt_pct(row.unrealized_gain_pct), gain_color))

            for col, fc_val in [
                (9, row.forecast_1y),
                (10, row.forecast_2y),
                (11, row.forecast_5y),
                (12, row.forecast_10y),
            ]:
                self.table.setItem(r, col, item(_fmt_money(fc_val)))

            # Store product_id in first column
            self.table.item(r, 0).setData(Qt.ItemDataRole.UserRole, row.product_id)

    def _render_chart(self, rows: list[PortfolioRow]):
        self.chart.clear()
        if not rows:
            return

        # Build actual portfolio value history
        all_product_ids = [r.product_id for r in rows]
        owned = repository.get_owned_quantities()

        # Gather price history for all owned products
        history_by_product = {}
        for row in rows:
            history = repository.get_price_history(row.product_id, days=730)
            if history:
                history_by_product[row.product_id] = history

        if not history_by_product:
            return

        # Collect all timestamps, compute portfolio value per day
        all_ts = sorted(set(
            r.recorded_at.timestamp()
            for hist in history_by_product.values()
            for r in hist
        ))
        if len(all_ts) < 2:
            return

        portfolio_values = []
        for ts in all_ts:
            total = 0.0
            for row in rows:
                hist = history_by_product.get(row.product_id, [])
                # Find latest price at or before ts
                price = None
                for rec in reversed(hist):
                    if rec.recorded_at.timestamp() <= ts:
                        price = rec.market_price or rec.mid_price
                        break
                if price and row.quantity:
                    total += price * row.quantity
            portfolio_values.append(total)

        xs = np.array(all_ts)
        ys = np.array(portfolio_values)

        self.chart.plot(xs, ys, pen=pg.mkPen("#388bfd", width=2), name="Portfolio Value")

        # Projected lines from latest data point
        if len(xs):
            last_ts = xs[-1]
            total_invested = sum(r.cost_basis for r in rows)

            for horizon, attr, color in [
                (1, "forecast_1y", FORECAST_COLORS[1]),
                (2, "forecast_2y", FORECAST_COLORS[2]),
                (5, "forecast_5y", FORECAST_COLORS[5]),
                (10, "forecast_10y", FORECAST_COLORS[10]),
            ]:
                proj_total = sum(getattr(r, attr) for r in rows if getattr(r, attr) is not None)
                if proj_total > 0:
                    future_ts = last_ts + horizon * 365.25 * 86400
                    self.chart.plot(
                        np.array([last_ts, future_ts]),
                        np.array([ys[-1], proj_total]),
                        pen=pg.mkPen(color, width=1.5, style=Qt.PenStyle.DotLine),
                        name=f"{horizon}Y Projected"
                    )

    def _show_context_menu(self, pos):
        from PyQt6.QtWidgets import QMenu
        from PyQt6.QtGui import QAction
        row = self.table.rowAt(pos.y())
        if row < 0:
            return
        item = self.table.item(row, 0)
        if not item:
            return
        product_id = item.data(Qt.ItemDataRole.UserRole)
        if not product_id:
            return

        menu = QMenu(self)
        action = menu.addAction("Edit Holdings...")
        action.triggered.connect(lambda: self.manage_product_requested.emit(product_id))
        menu.exec(self.table.viewport().mapToGlobal(pos))

    def _export_csv(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Portfolio", "portfolio.csv", "CSV Files (*.csv)"
        )
        if not path:
            return
        cols = self.table.columnCount()
        headers = [self.table.horizontalHeaderItem(c).text() for c in range(cols)]
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            for r in range(self.table.rowCount()):
                writer.writerow([
                    (self.table.item(r, c).text() if self.table.item(r, c) else "")
                    for c in range(cols)
                ])
        QMessageBox.information(self, "Exported", f"Portfolio saved to:\n{path}")
