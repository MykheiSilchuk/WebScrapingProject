import logging
from scr.orchestration.orchestrator import ScrapingOrchestrator

# Імпортуємо конкретні реалізації, які будемо передавати оркестратору
from scr.implementation.web_scraper import WebScraper 
from scr.implementation.database import DatabaseManager  
from scr.implementation.product_extractor import ProductExtractor  

import config # Потрібен для передачі конфігурації при ініціалізації

# --- Configure Logging for the entire application (moved here as the entry point) ---
logging.basicConfig(
    level=logging.INFO, # Default logging level for console output
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

logger = logging.getLogger(__name__) # Logger for the main script

if __name__ == "__main__":
    logger.info("Application started. Initializing ScrapingOrchestrator.")
    
    # 1. Створюємо конкретні реалізації залежностей
    # Ці об'єкти будуть "ін'єктовані" в оркестратор
    main_scraper_instance = WebScraper(
        base_url=config.SCRAPER_BASE_URL, 
        headers=config.HEADERS
    )
    db_manager_instance = DatabaseManager()
    product_extractor_instance = ProductExtractor()

    # 2. Передаємо (ін'єктуємо) ці реалізації в ScrapingOrchestrator
    orchestrator = ScrapingOrchestrator(
        scraper=main_scraper_instance,
        db_manager=db_manager_instance,
        extractor=product_extractor_instance # Передаємо екстрактор
    )
    
    orchestrator.run_scraping()
    logger.info("Application finished.")