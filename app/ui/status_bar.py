"""Status bar: last-updated label + Refresh Now button + progress."""
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton, QProgressBar
from PyQt6.QtCore import pyqtSignal, Qt


class StatusBar(QWidget):
    refresh_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(10)

        self.last_updated_label = QLabel("Last updated: Never")
        layout.addWidget(self.last_updated_label)

        self.source_label = QLabel("")
        self.source_label.setStyleSheet("color: #8b949e; font-size: 11px;")
        layout.addWidget(self.source_label)

        layout.addStretch()

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedWidth(200)
        self.progress_bar.setFixedHeight(14)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.progress_label = QLabel("")
        self.progress_label.setStyleSheet("color: #8b949e; font-size: 11px;")
        layout.addWidget(self.progress_label)

        self.refresh_btn = QPushButton("Refresh Now")
        self.refresh_btn.setObjectName("refreshButton")
        self.refresh_btn.setFixedWidth(110)
        self.refresh_btn.clicked.connect(self.refresh_requested)
        layout.addWidget(self.refresh_btn)

    def set_last_updated(self, timestamp: str):
        self.last_updated_label.setText(f"Last updated: {timestamp}")

    def set_refreshing(self, is_refreshing: bool):
        self.refresh_btn.setEnabled(not is_refreshing)
        self.progress_bar.setVisible(is_refreshing)
        if not is_refreshing:
            self.progress_label.setText("")

    def set_progress(self, current: int, total: int):
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        self.progress_label.setText(f"{current}/{total}")

    def set_source_info(self, text: str):
        self.source_label.setText(text)
