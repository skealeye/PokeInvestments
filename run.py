"""Entry point for PokemonInvestments application."""
import sys
import logging
from pathlib import Path

# Configure logging before imports that use it
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from app.data.database import create_all_tables
from app.data.seed_data import upsert_all
from app.main_window import MainWindow
from app.ui.styles import DARK_STYLE


def main():
    # Database setup
    logging.info("Initialising database...")
    create_all_tables()
    upsert_all()
    logging.info("Seed data loaded.")

    # Qt app
    app = QApplication(sys.argv)
    app.setApplicationName("PokemonInvestments")
    app.setOrganizationName("PokemonInvestments")
    app.setStyleSheet(DARK_STYLE)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
