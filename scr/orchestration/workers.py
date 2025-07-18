import logging
import queue

# Імпортуємо абстрактні класи для тайп-хінтів та для кращої гнучкості
from scr.core.abstract_scraper import AbstractWebScraper
from scr.core.abstract_extractor import AbstractProductExtractor
from scr.core.abstract_database_manager import AbstractDatabaseManager

from lxml.html import HtmlElement 

logger = logging.getLogger(__name__)

def scrape_product_worker(
    worker_id: int,
    product_url_queue: queue.Queue,
    data_to_write_queue: queue.Queue,
    # Приймаємо ін'єктовані залежності
    scraper: AbstractWebScraper,
    extractor: AbstractProductExtractor,
    sleep_between_product_pages: int
):
    """
    Worker function for fetching and extracting product details.
    Runs in a separate thread from the ThreadPoolExecutor.
    Receives necessary dependencies via arguments (Dependency Injection).
    """
    # Воркер тепер використовує ін'єктований скрапер та екстрактор
    worker_scraper = scraper 
    worker_extractor = extractor

    processed_count = 0
    while True:
        try:
            product_info = product_url_queue.get(timeout=1.5)

            if product_info is None:
                product_url_queue.task_done()
                break 

            processed_count += 1
            product_url = product_info['url']
            product_name_on_listing = product_info['name_on_listing']
            product_category_on_listing = product_info['category_on_listing']

            logger.info(f"Worker {worker_id}: Processing '{product_name_on_listing}' from category '{product_category_on_listing}'")

            product_detail_tree = worker_scraper.fetch_page(
                product_url, sleep_time=sleep_between_product_pages
            )

            if product_detail_tree is not None:
                product_data = worker_extractor.extract_product_details(
                    product_tree=product_detail_tree,
                    listing_product_name=product_name_on_listing,
                    listing_category=product_category_on_listing
                )
                product_data['url'] = product_url 
                
                data_to_write_queue.put(product_data)
                logger.debug(f"Worker {worker_id}: Put data for '{product_data['product_name']}' into write queue.")
            else:
                logger.warning(f"Worker {worker_id}: Skipping data extraction for failed product page: {product_url}")

            product_url_queue.task_done() 
        except queue.Empty:
            logger.info(f"Worker {worker_id}: Product URL queue is empty, shutting down due to timeout.")
            break
        except Exception as e:
            logger.error(f"Worker {worker_id}: An error occurred: {e}", exc_info=True)
            if 'product_url_queue' in locals(): # Перевірка на випадок, якщо product_url_queue не визначена
                product_url_queue.task_done()

    # Скрапер worker_scraper більше не закриває сесію, оскільки він її не створював.
    # Сесія буде закрита оркестратором, який її створив.
    logger.info(f"Worker {worker_id} finished processing {processed_count} products.")


def database_writer_worker(data_to_write_queue: queue.Queue, db_manager: AbstractDatabaseManager): # <--- ЗМІНА ТУТ
    """
    Dedicated worker function for writing extracted product data to the database.
    Runs in a single separate thread. Receives db_manager via arguments.
    """
    logger.info("Database writer thread started.")
    processed_count = 0
    try:
        # Використовуємо ін'єктований db_manager як контекстний менеджер
        with db_manager as db: 
            while True:
                try:
                    product_data = data_to_write_queue.get(timeout=10) 

                    if product_data is None:
                        data_to_write_queue.task_done()
                        break 

                    try:
                        db.insert_product_data(product_data)
                        processed_count += 1
                        logger.info(f"DB Writer: ✓ Inserted/Updated data for '{product_data['product_name']}'. Total: {processed_count}")
                    except Exception as e:
                        logger.error(f"DB Writer: ✗ Failed to insert/update data for '{product_data.get('url', 'Unknown URL')}': {e}", exc_info=True)
                    finally:
                        data_to_write_queue.task_done()
                except queue.Empty:
                    logger.info("DB Writer: Data queue is empty, shutting down due to timeout.")
                    break
    except Exception as e:
        logger.critical(f"DB Writer: Critical error with database connection or operation: {e}", exc_info=True)
    finally:
        logger.info(f"Database writer thread finished. Wrote {processed_count} items.")