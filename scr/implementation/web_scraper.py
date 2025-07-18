# web_scraper.py
import requests
from lxml import html
import time
import logging

import config
from scr.core.abstract_scraper import AbstractWebScraper 

# Configure logging for this module
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO) # Set to INFO for general messages, DEBUG for more verbosity

# Змінюємо оголошення класу, щоб він успадковував від AbstractWebScraper
class WebScraper(AbstractWebScraper): # <--- ЗМІНА ТУТ
    """
    Handles making HTTP requests and parsing HTML content into lxml trees.
    Provides methods for fetching pages with error handling and rate limiting.
    """

    def __init__(self, base_url: str = config.SCRAPER_BASE_URL, headers: dict = config.HEADERS):
        """
        Initializes the WebScraper with a base URL and HTTP headers.

        Args:
            base_url (str): The base URL for the website to scrape.
            headers (dict): HTTP headers to use for requests.
        """
        self.base_url = base_url
        self.headers = headers
        self.session = requests.Session() # Use a session for persistent connections and header management
        logger.info(f"WebScraper initialized for base URL: {self.base_url}")

    def fetch_page(self, url: str, sleep_time: int = 0) -> html.HtmlElement | None:
        """
        Fetches a web page and returns its parsed lxml HTML tree.

        Args:
            url (str): The full URL of the page to fetch.
            sleep_time (int): Seconds to sleep before making the request (for rate limiting).

        Returns:
            lxml.html.HtmlElement | None: The parsed HTML tree if successful, None otherwise.
        """
        if sleep_time > 0:
            logger.debug(f"Sleeping for {sleep_time} seconds before fetching {url}")
            time.sleep(sleep_time)

        try:
            # Змінив логіку формування full_url для більшої надійності, враховуючи urljoin
            full_url = requests.compat.urljoin(self.base_url, url) if url.startswith('/') else url

            logger.info(f"Attempting to fetch: {full_url}")
            response = self.session.get(full_url, headers=self.headers, timeout=10) # Added timeout
            response.raise_for_status() # Raises HTTPError for bad responses (4xx or 5xx)

            # Use response.content for fromstring, as it expects bytes
            tree = html.fromstring(response.content)
            logger.info(f"✓ Successfully fetched and parsed: {full_url}")
            return tree
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Network or HTTP error fetching {full_url}: {e}")
            return None
        except html.etree.XMLSyntaxError as e:
            logger.error(f"✗❌ HTML parsing error for {full_url}: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ An unexpected error occurred while fetching {full_url}: {e}")
            return None

    def close_session(self):
        """Closes the requests session."""
        self.session.close()
        logger.info("Requests session closed.")