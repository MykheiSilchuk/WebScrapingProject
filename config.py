import os
from dotenv import load_dotenv

# Load environment variables from a .env file (if it exists)
# This is useful for local development. In production, env vars are set directly.
load_dotenv()

# --- Database Configuration ---
# These lines were commented out in your provided config.py.
# They need to be uncommented and correctly use os.getenv to read from the environment.
DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD") # IMPORTANT: Ensure this matches your .env or actual password!
DB_PORT = os.getenv("DB_PORT")

# --- Scraper Configuration ---
SCRAPER_BASE_URL = os.getenv("SCRAPER_BASE_URL")

SCRAPER_NEEDED_CATEGORIES = set(
    os.getenv(
        "SCRAPER_NEEDED_CATEGORIES",
        "devops,it-infrastructure,data-analytics-and-management"
    ).split(',')
)

SCRAPER_TEST_MODE = os.getenv("SCRAPER_TEST_MODE").lower() == "true"

HEADERS = {
    "User-Agent": (
        "Mozilla/50 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/114.0.0.0 Safari/537.36"
    )
}

# --- Rate Limiting ---
SLEEP_BETWEEN_CATEGORY_PAGES = int(os.getenv("SLEEP_BETWEEN_CATEGORY_PAGES"))
SLEEP_BETWEEN_PRODUCT_PAGES = int(os.getenv("SLEEP_BETWEEN_PRODUCT_PAGES"))

# --- Testing Limits (for SCRAPER_TEST_MODE) ---
TEST_PRODUCT_LIMIT = int(os.getenv("TEST_PRODUCT_LIMIT"))