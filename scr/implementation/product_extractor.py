from lxml import html
import logging
from scr.core.abstract_extractor import AbstractProductExtractor

# Configure logging for this module
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO) # Set to INFO for general messages, DEBUG for more verbosity

# Змінюємо оголошення класу, щоб він успадковував від AbstractProductExtractor
class ProductExtractor(AbstractProductExtractor):
    """
    Extracts specific product details from an lxml HTML tree.
    Adheres to SRP by focusing solely on data extraction from the HTML structure.
    """

    def __init__(self):
        """
        Initializes the ProductExtractor.
        No specific parameters needed for initialization as it operates on provided HTML trees.
        """
        logger.debug("ProductExtractor initialized.")

    def extract_product_details(self, product_tree: html.HtmlElement, listing_product_name: str, listing_category: str) -> dict:
        """
        Extracts various details for a single product from its HTML tree.

        Args:
            product_tree (lxml.html.HtmlElement): The parsed HTML tree of the product detail page.
            listing_product_name (str): Product name obtained from the category listing page,
                                         used as a fallback if detail page name is not found.
            listing_category (str): Category obtained from the category listing page,
                                     used as a fallback if detail page category is not found.

        Returns:
            dict: A dictionary containing the extracted product details.
        """
        product_details = {
            'product_name': listing_product_name, 
            'category': listing_category,       
            'price_median': "Not specified",
            'price_low': "Not specified",
            'price_high': "Not specified",
            'description': "No detailed description found."
        }

        # --- Extract Product Name ---
        product_name_detail_xpath = '//h1[@class="rt-Heading rt-r-size-5"]/text()'
        product_name_detail_element = product_tree.xpath(product_name_detail_xpath)
        if product_name_detail_element:
            product_details['product_name'] = product_name_detail_element[0].strip()
        logger.debug(f"Extracted Product Name: {product_details['product_name']}")

        # --- Extract Description ---
        description_xpath = '//div[contains(@class, "rt-Box _read-more-box__content_122o3_1")]'
        product_description_elements = product_tree.xpath(description_xpath)
        extracted_descriptions = []
        for elem in product_description_elements:
            text = elem.text_content().strip()
            # Filter out short or generic texts that are not actual descriptions
            if len(text) > 20 and not text.lower().startswith("what is") and not text.lower().startswith("how it works"):
                extracted_descriptions.append(text)
        if extracted_descriptions:
            product_details['description'] = "\n".join(extracted_descriptions)
        logger.debug(f"Extracted Description snippet: {product_details['description'][:100]}...")


        # --- Extract Median Price ---
        median_price_xpath = '//div[contains(@class, "rt-r-ai-end")]/span[@class="v-fw-700 v-fs-24"]/text()'
        median_price_span = product_tree.xpath(median_price_xpath)
        if median_price_span:
            product_details['price_median'] = median_price_span[0].strip()
        logger.debug(f"Extracted Median Price: {product_details['price_median']}")


        # --- Extract Price Range ---
        price_range_container_xpath = '//div[contains(@class, "rt-Grid") and contains(@class, "rt-r-gtc") and contains(@class, "_rangeSlider")]'
        price_range_container = product_tree.xpath(price_range_container_xpath)

        if price_range_container:
            low_price_xpath_relative = './span[1]/text()'
            low_price_element = price_range_container[0].xpath(low_price_xpath_relative)
            if low_price_element:
                product_details['price_low'] = low_price_element[0].strip()
            logger.debug(f"Extracted Low Price: {product_details['price_low']}")


            high_price_xpath_relative = './span[2]/text()'
            high_price_element = price_range_container[0].xpath(high_price_xpath_relative)
            if high_price_element:
                product_details['price_high'] = high_price_element[0].strip()
            logger.debug(f"Extracted High Price: {product_details['price_high']}")
        else:
            logger.debug("Price range container not found using the new XPath.")
        
        # --- Extract Category (from breadcrumbs if available) ---
        category_detail_xpath = '//nav[contains(@aria-label, "breadcrumb")]//a[contains(@href, "/categories/")]/text()'
        category_detail_element = product_tree.xpath(category_detail_xpath)
        if category_detail_element:
            product_details['category'] = category_detail_element[0].strip()
        # If not found in breadcrumbs, it retains the 'listing_category' fallback.
        logger.debug(f"Extracted Category: {product_details['category']}")

        return product_details