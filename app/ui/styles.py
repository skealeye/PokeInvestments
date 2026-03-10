"""Dark QSS theme - dark blue/gold palette."""

DARK_STYLE = """
QMainWindow, QDialog, QWidget {
    background-color: #0d1117;
    color: #c9d1d9;
    font-family: "Segoe UI", Arial, sans-serif;
    font-size: 13px;
}

QTabWidget::pane {
    border: 1px solid #21262d;
    background-color: #0d1117;
}

QTabBar::tab {
    background-color: #161b22;
    color: #8b949e;
    padding: 8px 20px;
    border: 1px solid #21262d;
    border-bottom: none;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
}

QTabBar::tab:selected {
    background-color: #0d1117;
    color: #f0c040;
    border-bottom: 2px solid #f0c040;
}

QTabBar::tab:hover:!selected {
    color: #c9d1d9;
    background-color: #21262d;
}

QTableView {
    background-color: #0d1117;
    gridline-color: #21262d;
    border: 1px solid #21262d;
    selection-background-color: #1f3a5f;
    selection-color: #ffffff;
    alternate-background-color: #161b22;
}

QTableView::item {
    padding: 4px 8px;
}

QHeaderView::section {
    background-color: #161b22;
    color: #f0c040;
    font-weight: bold;
    padding: 6px 8px;
    border: none;
    border-right: 1px solid #21262d;
    border-bottom: 1px solid #f0c040;
}

QHeaderView::section:hover {
    background-color: #21262d;
}

QPushButton {
    background-color: #1f3a5f;
    color: #c9d1d9;
    border: 1px solid #388bfd;
    border-radius: 4px;
    padding: 6px 14px;
    font-weight: 600;
}

QPushButton:hover {
    background-color: #388bfd;
    color: #ffffff;
}

QPushButton:pressed {
    background-color: #1158c7;
}

QPushButton:disabled {
    background-color: #21262d;
    color: #484f58;
    border-color: #30363d;
}

QPushButton#refreshButton {
    background-color: #1a4731;
    border-color: #2ea043;
    color: #3fb950;
}

QPushButton#refreshButton:hover {
    background-color: #2ea043;
    color: #ffffff;
}

QPushButton#dangerButton {
    background-color: #4a1b1b;
    border-color: #f85149;
    color: #f85149;
}

QPushButton#dangerButton:hover {
    background-color: #f85149;
    color: #ffffff;
}

QLineEdit, QDoubleSpinBox, QSpinBox, QDateEdit, QComboBox {
    background-color: #161b22;
    color: #c9d1d9;
    border: 1px solid #30363d;
    border-radius: 4px;
    padding: 5px 8px;
}

QLineEdit:focus, QDoubleSpinBox:focus, QSpinBox:focus, QDateEdit:focus, QComboBox:focus {
    border-color: #388bfd;
}

QComboBox::drop-down {
    border: none;
}

QComboBox QAbstractItemView {
    background-color: #161b22;
    color: #c9d1d9;
    selection-background-color: #1f3a5f;
}

QScrollBar:vertical {
    background-color: #0d1117;
    width: 10px;
    border: none;
}

QScrollBar::handle:vertical {
    background-color: #30363d;
    border-radius: 5px;
    min-height: 20px;
}

QScrollBar::handle:vertical:hover {
    background-color: #484f58;
}

QScrollBar:horizontal {
    background-color: #0d1117;
    height: 10px;
    border: none;
}

QScrollBar::handle:horizontal {
    background-color: #30363d;
    border-radius: 5px;
    min-width: 20px;
}

QScrollBar::add-line, QScrollBar::sub-line {
    border: none;
    background: none;
}

QStatusBar {
    background-color: #161b22;
    color: #8b949e;
    border-top: 1px solid #21262d;
}

QLabel {
    color: #c9d1d9;
}

QLabel#cardTitle {
    color: #8b949e;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 1px;
}

QLabel#cardValue {
    color: #f0c040;
    font-size: 22px;
    font-weight: 700;
}

QLabel#cardValueGreen {
    color: #3fb950;
    font-size: 22px;
    font-weight: 700;
}

QLabel#cardValueRed {
    color: #f85149;
    font-size: 22px;
    font-weight: 700;
}

QFrame#card {
    background-color: #161b22;
    border: 1px solid #21262d;
    border-radius: 8px;
}

QFrame#cardGold {
    background-color: #161b22;
    border: 1px solid #f0c040;
    border-radius: 8px;
}

QProgressBar {
    background-color: #21262d;
    border: 1px solid #30363d;
    border-radius: 4px;
    text-align: center;
    color: #c9d1d9;
}

QProgressBar::chunk {
    background-color: #388bfd;
    border-radius: 3px;
}

QGroupBox {
    color: #f0c040;
    border: 1px solid #30363d;
    border-radius: 4px;
    margin-top: 8px;
    padding-top: 8px;
    font-weight: 600;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 8px;
    padding: 0 4px;
}

QSplitter::handle {
    background-color: #21262d;
}

QToolTip {
    background-color: #161b22;
    color: #c9d1d9;
    border: 1px solid #f0c040;
    padding: 4px;
}

QMenuBar {
    background-color: #161b22;
    color: #c9d1d9;
}

QMenuBar::item:selected {
    background-color: #21262d;
}

QMenu {
    background-color: #161b22;
    color: #c9d1d9;
    border: 1px solid #30363d;
}

QMenu::item:selected {
    background-color: #1f3a5f;
}
"""
