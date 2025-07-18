import time
import logging
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed
import queue
import threading
import os

# Import all custom modules
import config
# Імпортуємо абстрактні класи замість конкретних реалізацій
from scr.core.abstract_database_manager import AbstractDatabaseManager 
from scr.core.abstract_scraper import AbstractWebScraper 
from scr.core.abstract_extractor import AbstractProductExtractor 

# Імпортуємо конкретні реалізації, які БУДУТЬ передаватися
from scr.implementation.database import DatabaseManager 
from scr.implementation.web_scraper import WebScraper
from scr.implementation.product_extractor import ProductExtractor

from lxml.html import HtmlElement 

# Import the worker functions
from scr.orchestration.workers import scrape_product_worker, database_writer_worker 

logger = logging.getLogger(__name__)

class ScrapingOrchestrator:
    """
    Orchestrates the entire web scraping process using a multithreaded producer-consumer model.
    Manages fetching product pages concurrently and writing data to the database in a dedicated thread.
    """

    # Конструктор тепер приймає абстракції як аргументи
    def __init__(
        self, 
        scraper: AbstractWebScraper,
        db_manager: AbstractDatabaseManager,
        extractor: AbstractProductExtractor
    ):
        """
        Initializes the orchestrator with its dependencies and thread-safe queues.
        Dependencies (scraper, db_manager, extractor) are injected.
        """
        self.main_scraper = scraper # Використовуємо ін'єктований скрапер
        self.db_manager = db_manager # Використовуємо ін'єктований менеджер БД
        self.extractor = extractor # Використовуємо ін'єктований екстрактор

        self.base_url = config.SCRAPER_BASE_URL
        self.needed_categories = config.SCRAPER_NEEDED_CATEGORIES
        self.test_mode = config.SCRAPER_TEST_MODE
        self.test_product_limit = config.TEST_PRODUCT_LIMIT
        self.sleep_between_category_pages = config.SLEEP_BETWEEN_CATEGORY_PAGES
        self.sleep_between_product_pages = config.SLEEP_BETWEEN_PRODUCT_PAGES
        
        # --- Queues for multithreading ---
        self.product_url_queue = queue.Queue()
        self.data_to_write_queue = queue.Queue()

        self.scraper_thread_count = int(os.getenv("SCRAPER_THREAD_COUNT", "5"))

        logger.info(f"ScrapingOrchestrator initialized. Using {self.scraper_thread_count} threads for scraping.")
        logger.info(f"Test Mode: {self.test_mode}, Test Product Limit: {self.test_product_limit}")

    def _get_category_links(self) -> list[str]:
        """Scrapes the main page to find relevant category links."""
        logger.info(f"Fetching main page: {self.base_url} to discover categories.")
        # Використовуємо self.main_scraper
        main_page_tree = self.main_scraper.fetch_page(self.base_url, sleep_time=0)

        if main_page_tree is None:
            logger.error("Failed to fetch main page. Cannot find category links.")
            return []

        buttons_xpath = '//button[@class="_button_3ftu4_1 _stylePrimary_3ftu4_39 _sizeDefault_3ftu4_12 _departmentPill_sticr_199"]'
        buttons = main_page_tree.xpath(buttons_xpath)
        logger.info(f"Found {len(buttons)} potential category buttons.")

        all_links = []
        for btn in buttons:
            link_elements = btn.xpath('.//a[@href]')
            if link_elements:
                href = link_elements[0].get('href')
                all_links.append(href)

        needed_links = []
        for link in all_links:
            if any(category_keyword in link for category_keyword in self.needed_categories):
                needed_links.append(link)
        
        logger.info(f"✓ Identified {len(needed_links)} category links matching needed criteria: {self.needed_categories}")
        return needed_links

    def _get_product_links_from_category_page(self, category_url: str, page_tree: HtmlElement) -> list[dict]:
        """
        Extracts product links and their basic info (name, category) from a category page.
        """
        product_links_xpath = '//a[@href and contains(@class, "rt-Link") and @data-discover="true"][@href[starts-with(., "/marketplace/")]]'
        product_link_elements = page_tree.xpath(product_links_xpath)
        
        products_on_this_category_page = []
        current_category_slug = category_url.split('/')[-1]

        for product_link_elem in product_link_elements:
            href = product_link_elem.get('href')
            if not href:
                logger.warning(f"Found product link element without href on {category_url}.")
                continue
            
            name_element = product_link_elem.xpath('.//span[@class="rt-Text rt-r-size-2 rt-truncate"]')
            product_name = name_element[0].text_content().strip() if name_element else "Unknown Product Name"
            
            full_product_url = urljoin(self.base_url, href)
            
            products_on_this_category_page.append({
                'name_on_listing': product_name,
                'url': full_product_url,
                'category_on_listing': current_category_slug
            })
        
        logger.info(f"  Found {len(products_on_this_category_page)} product links on category page: {current_category_slug}")
        return products_on_this_category_page


    def run_scraping(self):
        """
        Executes the full scraping workflow using multithreading.
        """
        start_time = time.perf_counter()
        logger.info("Starting the full scraping process with multithreading.")

        try:
            # Викликаємо метод на ін'єктованому db_manager
            self.db_manager.create_products_table()

            # Phase 1: Get category links (sequential)
            category_links = self._get_category_links()
            if not category_links:
                logger.error("No relevant category links found. Exiting.")
                return

            # Phase 2: Scrape category pages for product links (sequential, populating product_url_queue)
            all_products_from_categories = []
            for i, link in enumerate(category_links):
                logger.info(f"Processing category page {i+1}/{len(category_links)}: {link}")
                # Використовуємо self.main_scraper
                category_page_tree = self.main_scraper.fetch_page(link, sleep_time=self.sleep_between_category_pages)
                
                if category_page_tree is not None:
                    products_on_page = self._get_product_links_from_category_page(link, category_page_tree)
                    all_products_from_categories.extend(products_on_page)
                else:
                    logger.warning(f"Skipping product link extraction for failed category page: {link}")

            # Deduplicate products by URL and populate the product_url_queue
            unique_products_to_process = {p['url']: p for p in all_products_from_categories}.values()
            
            if self.test_mode:
                limited_products = list(unique_products_to_process)[:self.test_product_limit]
                logger.info(f"Test mode active: Limiting to {len(limited_products)} products for scraping.")
                for product_info in limited_products:
                    self.product_url_queue.put(product_info)
            else:
                for product_info in unique_products_to_process:
                    self.product_url_queue.put(product_info)

            logger.info(f"Product URL queue populated with {self.product_url_queue.qsize()} unique products.")
            if self.product_url_queue.empty():
                logger.warning("No products to scrape after processing categories and applying limits. Exiting.")
                return


            # --- Phase 3: Start multithreaded scraping and database writing ---

            # Start the dedicated database writer thread
            db_writer_thread = threading.Thread(
                target=database_writer_worker, 
                args=(self.data_to_write_queue, self.db_manager), # Передаємо ін'єктований db_manager
                daemon=True 
            )
            db_writer_thread.start()

            # Start the scraper worker threads
            with ThreadPoolExecutor(max_workers=self.scraper_thread_count) as executor:
                futures = []
                for i in range(self.scraper_thread_count):
                    future = executor.submit(
                        scrape_product_worker, 
                        i + 1,
                        self.product_url_queue,
                        self.data_to_write_queue,
                        # Передаємо ін'єктовані залежності воркерам, щоб вони їх використовували
                        self.main_scraper, # Передаємо сам ін'єктований скрапер
                        self.extractor, # Передаємо ін'єктований екстрактор
                        self.sleep_between_product_pages 
                    )
                    futures.append(future)

                # Wait for all product fetching tasks to be marked as done in the queue
                self.product_url_queue.join()
                logger.info("All product URL fetching tasks completed by worker threads.")

                # Signal scraper workers to shut down by putting sentinel values (None)
                for _ in range(self.scraper_thread_count):
                    self.product_url_queue.put(None)
                
                # Wait for worker threads to finish their execution gracefully
                for future in as_completed(futures):
                    try:
                        future.result() 
                    except Exception as exc:
                        logger.error(f'Worker thread generated an exception: {exc}', exc_info=True)

            logger.info("All scraper workers have shut down.")

            # Signal the database writer to shut down by putting a sentinel value
            self.data_to_write_queue.put(None)
            
            # Wait for the database writer thread to finish
            db_writer_thread.join(timeout=300) 
            if db_writer_thread.is_alive():
                logger.error("Database writer thread did not shut down gracefully within timeout.")

            logger.info("Database writer thread has shut down.")

        except Exception as e:
            logger.critical(f"A critical error occurred during the overall scraping process: {e}", exc_info=True)
        finally:
            self.main_scraper.close_session() # Закриваємо сесію основного скрапера
            end_time = time.perf_counter()
            total_execution_time = end_time - start_time
            logger.info(f"\n{'='*60}")
            logger.info("SCRAPING PROCESS COMPLETE")
            logger.info(f"Total script execution time: {total_execution_time:.2f} seconds")
            logger.info(f"{'='*60}\n")