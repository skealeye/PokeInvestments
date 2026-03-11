"""Application-wide settings and paths."""
import os
from pathlib import Path

APP_NAME = "PokemonInvestments"
APP_DATA_DIR = Path(os.environ.get("APPDATA", Path.home())) / APP_NAME
DB_PATH = APP_DATA_DIR / "pokemon_investments.db"

# Ensure data directory exists on import
APP_DATA_DIR.mkdir(parents=True, exist_ok=True)

# Price source priority
PRICE_SOURCES = ["tcgcsv", "price_tracker", "pokewallet"]

# Refresh settings
DEFAULT_REFRESH_INTERVAL_HOURS = 24

# Forecast horizons in years
FORECAST_HORIZONS = [1, 2, 5, 10]
MIN_HISTORY_DAYS_FOR_FORECAST = 1

# TCGCSV constants
TCGCSV_BASE_URL = "https://tcgcsv.com"
TCGCSV_POKEMON_CATEGORY = 3  # Pokemon category ID on TCGPlayer/TCGCSV

# HTTP settings
HTTP_TIMEOUT = 30.0
HTTP_MAX_RETRIES = 3
