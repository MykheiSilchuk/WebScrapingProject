import abc
import psycopg2

class AbstractDatabaseManager(abc.ABC):
    """
    Абстрактний базовий клас для керування з'єднаннями та операціями з базою даних.
    Визначає інтерфейс, який повинні реалізовувати конкретні менеджери БД.
    """

    @abc.abstractmethod
    def create_products_table(self):
        """
        Абстрактний метод для створення таблиці продуктів, якщо вона не існує.
        """
        pass

    @abc.abstractmethod
    def insert_product_data(self, product_data: dict):
        """
        Абстрактний метод для вставки або оновлення даних про продукт.
        """
        pass

    # Також варто включити методи контекстного менеджера в інтерфейс,
    # щоб будь-яка реалізація могла використовуватися з "with"
    @abc.abstractmethod
    def __enter__(self):
        """
        Абстрактний метод для входу в контекст (встановлення з'єднання).
        """
        pass

    @abc.abstractmethod
    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Абстрактний метод для виходу з контексту (коміт/відкат і закриття з'єднання).
        """
        pass

