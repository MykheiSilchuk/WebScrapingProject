import abc
from lxml import html

class AbstractWebScraper(abc.ABC):
    """
    Абстрактний базовий клас для веб-скраперів.
    Визначає інтерфейс, який повинні реалізовувати конкретні скрапери.
    """

    @abc.abstractmethod
    def fetch_page(self, url: str, sleep_time: int = 0) -> html.HtmlElement | None:
        """
        Абстрактний метод для отримання веб-сторінки та її парсингу.
        """
        pass

    @abc.abstractmethod
    def close_session(self):
        """
        Абстрактний метод для закриття будь-яких відкритих сесій.
        """
        pass