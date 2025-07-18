# abstract_extractor.py
import abc
from lxml import html

class AbstractProductExtractor(abc.ABC):
    """
    Абстрактний базовий клас для вилучення деталей продукту з HTML-дерева.
    Визначає інтерфейс, який повинні реалізовувати конкретні екстрактори.
    """

    @abc.abstractmethod
    def extract_product_details(self, product_tree: html.HtmlElement, listing_product_name: str, listing_category: str) -> dict:
        """
        Абстрактний метод для вилучення деталей продукту зі сторінки.

        Args:
            product_tree (lxml.html.HtmlElement): Розпаршене HTML-дерево сторінки продукту.
            listing_product_name (str): Назва продукту з каталогу, використовується як запасний варіант.
            listing_category (str): Категорія продукту з каталогу, використовується як запасний варіант.

        Returns:
            dict: Словник з вилученими деталями продукту.
        """
        pass