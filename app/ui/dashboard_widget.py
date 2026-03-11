"""Dashboard: QTableView with all products, current prices, forecasts, owned qty."""
import csv
import os
from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTableView, QAbstractItemView,
    QHeaderView, QMenu, QFileDialog, QMessageBox
)
from PyQt6.QtCore import (
    Qt, QAbstractTableModel, QModelIndex, QSortFilterProxyModel,
    pyqtSignal, QVariant
)
from PyQt6.QtGui import QColor, QFont, QAction

from app.data.models import Product, PriceRecord, Forecast
from app.data import repository
from app.ui.filter_bar import FilterBar


COLUMNS = [
    "Set", "Product", "Type", "Market Price",
    "1Y Forecast", "2Y Forecast", "5Y Forecast", "10Y Forecast",
    "Owned", "Source"
]

COL_SET = 0
COL_PRODUCT = 1
COL_TYPE = 2
COL_MARKET = 3
COL_1Y = 4
COL_2Y = 5
COL_5Y = 6
COL_10Y = 7
COL_OWNED = 8
COL_SOURCE = 9

TYPE_DISPLAY = {
    "booster_box": "Booster Box",
    "etb": "ETB",
    "pc_etb": "PC ETB",
}


class DashboardModel(QAbstractTableModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._products: list[Product] = []
        self._prices: dict[int, PriceRecord] = {}
        self._forecasts: dict[tuple[int, int], Forecast] = {}
        self._owned: dict[int, int] = {}

    def load(self, products, prices, forecasts, owned):
        self.beginResetModel()
        self._products = products
        self._prices = prices
        self._forecasts = forecasts
        self._owned = owned
        self.endResetModel()

    def update_price(self, product_id: int, market_price: float):
        for i, p in enumerate(self._products):
            if p.id == product_id:
                # Create/update price record in cache
                existing = self._prices.get(product_id)
                if existing:
                    existing.market_price = market_price
                self.dataChanged.emit(
                    self.index(i, COL_MARKET),
                    self.index(i, COL_MARKET)
                )
                break

    def update_owned(self, owned: dict[int, int]):
        self._owned = owned
        self.dataChanged.emit(
            self.index(0, COL_OWNED),
            self.index(len(self._products) - 1, COL_OWNED)
        )

    def update_forecasts(self, forecasts: dict[tuple[int, int], Forecast]):
        self._forecasts = forecasts
        self.dataChanged.emit(
            self.index(0, COL_1Y),
            self.index(len(self._products) - 1, COL_10Y)
        )

    def rowCount(self, parent=QModelIndex()):
        return len(self._products)

    def columnCount(self, parent=QModelIndex()):
        return len(COLUMNS)

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return COLUMNS[section]
        return None

    def data(self, index: QModelIndex, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or index.row() >= len(self._products):
            return None

        p = self._products[index.row()]
        col = index.column()
        price = self._prices.get(p.id)

        if role == Qt.ItemDataRole.DisplayRole:
            return self._display_data(p, col, price)

        if role == Qt.ItemDataRole.ForegroundRole:
            return self._fg_color(p, col, price)

        if role == Qt.ItemDataRole.TextAlignmentRole:
            if col in (COL_MARKET, COL_1Y, COL_2Y, COL_5Y, COL_10Y):
                return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            if col == COL_OWNED:
                return Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
            return Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter

        if role == Qt.ItemDataRole.UserRole:
            return p.id

        return None

    def _display_data(self, p: Product, col: int, price: Optional[PriceRecord]) -> str:
        if col == COL_SET:
            return p.set_name or ""
        if col == COL_PRODUCT:
            return p.name
        if col == COL_TYPE:
            return TYPE_DISPLAY.get(p.product_type, p.product_type)
        if col == COL_MARKET:
            return f"${price.market_price:.2f}" if price and price.market_price else "N/A"
        if col in (COL_1Y, COL_2Y, COL_5Y, COL_10Y):
            horizon = {COL_1Y: 1, COL_2Y: 2, COL_5Y: 5, COL_10Y: 10}[col]
            f = self._forecasts.get((p.id, horizon))
            if f:
                return f"${f.predicted_price:.2f}"
            return "—"
        if col == COL_OWNED:
            qty = self._owned.get(p.id, 0)
            return str(qty) if qty > 0 else "—"
        if col == COL_SOURCE:
            return price.source if price else ""
        return ""

    def _fg_color(self, p, col, price):
        if col == COL_OWNED:
            qty = self._owned.get(p.id, 0)
            if qty > 0:
                return QColor("#f0c040")
        if col in (COL_1Y, COL_2Y, COL_5Y, COL_10Y):
            horizon = {COL_1Y: 1, COL_2Y: 2, COL_5Y: 5, COL_10Y: 10}[col]
            f = self._forecasts.get((p.id, horizon))
            if f and price and price.market_price:
                color = "#3fb950" if f.predicted_price > price.market_price else "#f85149"
                return QColor(color)
        return None

    def get_product_at(self, row: int) -> Optional[Product]:
        if 0 <= row < len(self._products):
            return self._products[row]
        return None

    def export_csv(self, path: str):
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(COLUMNS)
            for row in range(self.rowCount()):
                writer.writerow([
                    self.data(self.index(row, col))
                    for col in range(self.columnCount())
                ])


class DashboardFilterProxy(QSortFilterProxyModel):
    def __init__(self, filter_bar: FilterBar, owned: dict[int, int], parent=None):
        super().__init__(parent)
        self._filter_bar = filter_bar
        self._owned = owned
        self.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)

    def update_owned(self, owned: dict[int, int]):
        self._owned = owned
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        model = self.sourceModel()
        p = model.get_product_at(source_row)
        if p is None:
            return True
        owned_qty = self._owned.get(p.id, 0)
        return self._filter_bar.matches(p.name, p.set_name or "", p.product_type, owned_qty)


class DashboardWidget(QWidget):
    product_selected = pyqtSignal(object)     # Product
    manage_holdings_requested = pyqtSignal(object)  # Product

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self._load_data()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.filter_bar = FilterBar()
        self.filter_bar.filters_changed.connect(self._apply_filter)
        layout.addWidget(self.filter_bar)

        self._model = DashboardModel()
        self._proxy = DashboardFilterProxy(self.filter_bar, {})
        self._proxy.setSourceModel(self._model)

        self.table = QTableView()
        self.table.setModel(self._proxy)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        self.table.doubleClicked.connect(self._on_double_click)
        self.table.setSortingEnabled(True)

        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(COL_SET, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(COL_PRODUCT, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(COL_TYPE, QHeaderView.ResizeMode.ResizeToContents)
        for col in (COL_MARKET, COL_1Y, COL_2Y, COL_5Y, COL_10Y):
            hh.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(COL_OWNED, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(COL_SOURCE, QHeaderView.ResizeMode.ResizeToContents)

        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(True)
        layout.addWidget(self.table)

    def _load_data(self):
        products = repository.get_all_products()
        prices = repository.get_latest_prices_all()
        forecasts = repository.get_all_latest_forecasts()
        owned = repository.get_owned_quantities()

        set_names = sorted(set(p.set_name for p in products if p.set_name))
        self.filter_bar.populate_sets(set_names)

        self._proxy.update_owned(owned)
        self._model.load(products, prices, forecasts, owned)

    def refresh_data(self):
        self._load_data()

    def on_price_updated(self, product_id: int, market_price: float):
        self._model.update_price(product_id, market_price)

    def on_forecasts_updated(self):
        forecasts = repository.get_all_latest_forecasts()
        self._model.update_forecasts(forecasts)

    def on_inventory_changed(self):
        owned = repository.get_owned_quantities()
        self._model.update_owned(owned)
        self._proxy.update_owned(owned)

    def _apply_filter(self):
        self._proxy.invalidateFilter()

    def _on_double_click(self, proxy_index: QModelIndex):
        source_index = self._proxy.mapToSource(proxy_index)
        product = self._model.get_product_at(source_index.row())
        if product:
            self.product_selected.emit(product)

    def _show_context_menu(self, pos):
        proxy_index = self.table.indexAt(pos)
        if not proxy_index.isValid():
            return
        source_index = self._proxy.mapToSource(proxy_index)
        product = self._model.get_product_at(source_index.row())
        if not product:
            return

        menu = QMenu(self)
        view_chart_action = QAction("View Price Chart", self)
        view_chart_action.triggered.connect(lambda: self.product_selected.emit(product))
        menu.addAction(view_chart_action)

        manage_action = QAction("Manage Holdings...", self)
        manage_action.triggered.connect(lambda: self.manage_holdings_requested.emit(product))
        menu.addAction(manage_action)

        menu.addSeparator()
        export_action = QAction("Export to CSV...", self)
        export_action.triggered.connect(self._export_csv)
        menu.addAction(export_action)

        menu.exec(self.table.viewport().mapToGlobal(pos))

    def _export_csv(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Dashboard", "pokemon_prices.csv",
            "CSV Files (*.csv)"
        )
        if path:
            self._model.export_csv(path)
            QMessageBox.information(self, "Export Complete", f"Exported to:\n{path}")
