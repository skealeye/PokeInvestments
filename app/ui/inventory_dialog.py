"""Inventory dialog: add/edit/delete purchase lots for a product."""
from datetime import date

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QSpinBox, QDoubleSpinBox, QDateEdit, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt, QDate, pyqtSignal
from PyQt6.QtGui import QColor

from app.data.models import Product, InventoryEntry
from app.data import repository


class InventoryDialog(QDialog):
    inventory_changed = pyqtSignal()

    def __init__(self, product: Product, parent=None):
        super().__init__(parent)
        self.product = product
        self._editing_entry: InventoryEntry | None = None
        self.setWindowTitle(f"Manage Holdings — {product.name}")
        self.setMinimumWidth(640)
        self.setMinimumHeight(480)
        self._build_ui()
        self._load_entries()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Product info
        info = QLabel(f"<b>{self.product.name}</b>")
        info.setStyleSheet("font-size: 14px; color: #f0c040;")
        layout.addWidget(info)

        # MSRP hint
        if self.product.msrp:
            msrp_label = QLabel(f"MSRP: ${self.product.msrp:.2f}")
            msrp_label.setStyleSheet("color: #8b949e; font-size: 11px;")
            layout.addWidget(msrp_label)

        # Entry form
        form_frame = QFrame()
        form_frame.setObjectName("card")
        form_layout = QFormLayout(form_frame)
        form_layout.setContentsMargins(12, 12, 12, 12)
        form_layout.setSpacing(8)

        self.qty_spin = QSpinBox()
        self.qty_spin.setRange(1, 9999)
        self.qty_spin.setValue(1)
        form_layout.addRow("Quantity:", self.qty_spin)

        self.price_spin = QDoubleSpinBox()
        self.price_spin.setRange(0.01, 99999.99)
        self.price_spin.setDecimals(2)
        self.price_spin.setPrefix("$ ")
        self.price_spin.setValue(self.product.msrp or 50.0)
        form_layout.addRow("Purchase Price (per unit):", self.price_spin)

        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setDisplayFormat("yyyy-MM-dd")
        form_layout.addRow("Purchase Date:", self.date_edit)

        self.notes_edit = QLineEdit()
        self.notes_edit.setPlaceholderText("Optional notes (e.g. eBay, local store...)")
        form_layout.addRow("Notes:", self.notes_edit)

        layout.addWidget(form_frame)

        # Form buttons
        form_btns = QHBoxLayout()
        self.add_btn = QPushButton("Add Purchase Lot")
        self.add_btn.clicked.connect(self._add_entry)
        form_btns.addWidget(self.add_btn)

        self.cancel_edit_btn = QPushButton("Cancel Edit")
        self.cancel_edit_btn.setVisible(False)
        self.cancel_edit_btn.clicked.connect(self._cancel_edit)
        form_btns.addWidget(self.cancel_edit_btn)

        form_btns.addStretch()
        layout.addLayout(form_btns)

        # Holdings table
        holdings_label = QLabel("Purchase Lots:")
        holdings_label.setStyleSheet("font-weight: 600; color: #c9d1d9;")
        layout.addWidget(holdings_label)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["Qty", "Price/Unit", "Total Cost", "Date", "Notes", "Actions"])
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table)

        # Summary
        self.summary_label = QLabel("")
        self.summary_label.setStyleSheet("color: #8b949e; font-size: 12px;")
        layout.addWidget(self.summary_label)

        # Close
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

    def _load_entries(self):
        entries = repository.get_inventory_for_product(self.product.id)
        self.table.setRowCount(0)
        for entry in entries:
            self._add_table_row(entry)
        self._update_summary(entries)

    def _add_table_row(self, entry: InventoryEntry):
        row = self.table.rowCount()
        self.table.insertRow(row)

        total = entry.quantity * entry.purchase_price

        for col, text in enumerate([
            str(entry.quantity),
            f"${entry.purchase_price:.2f}",
            f"${total:.2f}",
            str(entry.purchase_date),
            entry.notes or "",
        ]):
            item = QTableWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, entry.id)
            self.table.setItem(row, col, item)

        # Action buttons
        action_widget = QWidget()
        action_layout = QHBoxLayout(action_widget)
        action_layout.setContentsMargins(2, 2, 2, 2)
        action_layout.setSpacing(4)

        edit_btn = QPushButton("Edit")
        edit_btn.setFixedWidth(44)
        edit_btn.clicked.connect(lambda _, e=entry: self._edit_entry(e))
        action_layout.addWidget(edit_btn)

        del_btn = QPushButton("Del")
        del_btn.setFixedWidth(40)
        del_btn.setObjectName("dangerButton")
        del_btn.clicked.connect(lambda _, e=entry: self._delete_entry(e))
        action_layout.addWidget(del_btn)

        self.table.setCellWidget(row, 5, action_widget)

    def _update_summary(self, entries: list[InventoryEntry]):
        if not entries:
            self.summary_label.setText("No holdings recorded.")
            return
        total_qty = sum(e.quantity for e in entries)
        total_cost = sum(e.quantity * e.purchase_price for e in entries)
        avg_price = total_cost / total_qty
        self.summary_label.setText(
            f"Total: {total_qty} units | Total Invested: ${total_cost:.2f} | Avg Cost: ${avg_price:.2f}/unit"
        )

    def _add_entry(self):
        qty = self.qty_spin.value()
        price = self.price_spin.value()
        qdate = self.date_edit.date()
        purchase_date = date(qdate.year(), qdate.month(), qdate.day())
        notes = self.notes_edit.text().strip() or None

        if self._editing_entry:
            self._editing_entry.quantity = qty
            self._editing_entry.purchase_price = price
            self._editing_entry.purchase_date = purchase_date
            self._editing_entry.notes = notes
            repository.update_inventory_entry(self._editing_entry)
            self._cancel_edit()
        else:
            entry = InventoryEntry(
                id=None,
                product_id=self.product.id,
                quantity=qty,
                purchase_price=price,
                purchase_date=purchase_date,
                notes=notes,
            )
            repository.add_inventory_entry(entry)

        self._load_entries()
        self.inventory_changed.emit()

    def _edit_entry(self, entry: InventoryEntry):
        self._editing_entry = entry
        self.qty_spin.setValue(entry.quantity)
        self.price_spin.setValue(entry.purchase_price)
        qd = entry.purchase_date
        self.date_edit.setDate(QDate(qd.year, qd.month, qd.day))
        self.notes_edit.setText(entry.notes or "")
        self.add_btn.setText("Save Changes")
        self.cancel_edit_btn.setVisible(True)

    def _cancel_edit(self):
        self._editing_entry = None
        self.qty_spin.setValue(1)
        self.price_spin.setValue(self.product.msrp or 50.0)
        self.date_edit.setDate(QDate.currentDate())
        self.notes_edit.clear()
        self.add_btn.setText("Add Purchase Lot")
        self.cancel_edit_btn.setVisible(False)

    def _delete_entry(self, entry: InventoryEntry):
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Delete {entry.quantity} unit(s) purchased at ${entry.purchase_price:.2f}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            repository.delete_inventory_entry(entry.id)
            self._load_entries()
            self.inventory_changed.emit()
