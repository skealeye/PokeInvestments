"""Filter bar: set/type filters and sort controls."""
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QComboBox, QLineEdit
)
from PyQt6.QtCore import pyqtSignal


class FilterBar(QWidget):
    filters_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(8)

        layout.addWidget(QLabel("Search:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Filter by name...")
        self.search_edit.setFixedWidth(200)
        self.search_edit.textChanged.connect(self.filters_changed)
        layout.addWidget(self.search_edit)

        layout.addWidget(QLabel("Set:"))
        self.set_combo = QComboBox()
        self.set_combo.addItem("All Sets", None)
        self.set_combo.setFixedWidth(200)
        self.set_combo.currentIndexChanged.connect(self.filters_changed)
        layout.addWidget(self.set_combo)

        layout.addWidget(QLabel("Type:"))
        self.type_combo = QComboBox()
        self.type_combo.addItems(["All Types", "Booster Box", "ETB", "Pokemon Center ETB"])
        self.type_combo.setFixedWidth(160)
        self.type_combo.currentIndexChanged.connect(self.filters_changed)
        layout.addWidget(self.type_combo)

        layout.addWidget(QLabel("Owned:"))
        self.owned_combo = QComboBox()
        self.owned_combo.addItems(["All", "Owned Only", "Not Owned"])
        self.owned_combo.setFixedWidth(110)
        self.owned_combo.currentIndexChanged.connect(self.filters_changed)
        layout.addWidget(self.owned_combo)

        layout.addStretch()

    def populate_sets(self, set_names: list[str]):
        self.set_combo.blockSignals(True)
        current = self.set_combo.currentData()
        self.set_combo.clear()
        self.set_combo.addItem("All Sets", None)
        for name in set_names:
            self.set_combo.addItem(name, name)
        # Restore selection
        idx = self.set_combo.findData(current)
        if idx >= 0:
            self.set_combo.setCurrentIndex(idx)
        self.set_combo.blockSignals(False)

    @property
    def search_text(self) -> str:
        return self.search_edit.text().lower().strip()

    @property
    def selected_set(self) -> str | None:
        return self.set_combo.currentData()

    @property
    def selected_type(self) -> str | None:
        text = self.type_combo.currentText()
        mapping = {
            "Booster Box": "booster_box",
            "ETB": "etb",
            "Pokemon Center ETB": "pc_etb",
        }
        return mapping.get(text)

    @property
    def owned_filter(self) -> str:
        return self.owned_combo.currentText()

    def matches(self, product_name: str, set_name: str,
                product_type: str, owned_qty: int) -> bool:
        if self.search_text and self.search_text not in product_name.lower():
            return False
        if self.selected_set and self.selected_set != set_name:
            return False
        if self.selected_type and self.selected_type != product_type:
            return False
        ownf = self.owned_filter
        if ownf == "Owned Only" and owned_qty == 0:
            return False
        if ownf == "Not Owned" and owned_qty > 0:
            return False
        return True
