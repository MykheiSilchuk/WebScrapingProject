import psycopg2
from psycopg2 import sql
import logging
from scr.core.abstract_database_manager import AbstractDatabaseManager 
import config

# Configure logging for this module
logger = logging.getLogger(__name__)
# Set to INFO for general messages, DEBUG for more verbosity
# Changed some INFO to DEBUG in _connect/_disconnect for less verbose output during normal operation
logger.setLevel(logging.INFO) 

# Змінюємо оголошення класу, щоб він успадковував від AbstractDatabaseManager
class DatabaseManager(AbstractDatabaseManager):
    """
    Manages connections and operations with the PostgreSQL database.
    Adheres to SRP by handling only database-related concerns.
    """

    def __init__(self):
        """
        Initializes the DatabaseManager with connection parameters from config.
        """
        self.db_host = config.DB_HOST
        self.db_name = config.DB_NAME
        self.db_user = config.DB_USER
        self.db_password = config.DB_PASSWORD
        self.db_port = config.DB_PORT
        self.conn = None
        self.cur = None

    def _connect(self):
        """
        Establishes a connection to the PostgreSQL database.
        Handles connection errors gracefully.
        Only connects if no active connection exists.
        """
        # Check if connection is already active and not closed
        if self.conn is None or self.conn.closed:
            try:
                self.conn = psycopg2.connect(
                    host=self.db_host,
                    database=self.db_name,
                    user=self.db_user,
                    password=self.db_password,
                    port=self.db_port
                )
                self.cur = self.conn.cursor()
                logger.debug("✓ Database connection established.") # Debug level for frequent connections
            except psycopg2.Error as e:
                logger.error(f"✗ Database connection error: {e}")
                self.conn = None 
                self.cur = None
                raise 
        else:
            logger.debug("Database already connected.") # Indicate connection reuse

    def _disconnect(self):
        """
        Closes the database cursor and connection if they are open.
        """
        if self.cur:
            self.cur.close()
            self.cur = None
        if self.conn:
            self.conn.close()
            self.conn = None
        logger.debug("✓ Database connection closed.") # Debug level for frequent disconnections

    def create_products_table(self):
        """
        Ensures the 'products' table exists in the database.
        This method manages its own connection because it's a standalone setup operation
        that happens before the main scraping loop.
        """
        try:
            self._connect()
            create_table_query = """
            CREATE TABLE IF NOT EXISTS products (
                id SERIAL PRIMARY KEY,
                product_name VARCHAR(255) NOT NULL,
                category VARCHAR(255),
                price_median VARCHAR(50),
                price_low VARCHAR(50),
                price_high VARCHAR(50),
                description TEXT,
                url VARCHAR(500) UNIQUE NOT NULL
            );
            """
            self.cur.execute(create_table_query)
            self.conn.commit() # Commit immediately after table creation
            logger.info("✓ 'products' table ensured to exist or created successfully.")
        except Exception as e:
            logger.error(f"✗ Error creating 'products' table: {e}")
            raise 
        finally:
            self._disconnect()

    def insert_product_data(self, product_data: dict):
        """
        Inserts or updates product data into the 'products' table.
        This method ASSUMES an active connection (self.conn and self.cur are already set).
        It does NOT manage its own connection or commit/rollback.
        The caller (e.g., the database_writer_worker's context manager) is responsible
        for managing the connection and committing transactions.
        """
        # Critical check: ensure connection is active before trying to use it
        if self.conn is None or self.cur is None or self.conn.closed:
            logger.error("Attempted to insert data without an active database connection. This indicates a logic error in the calling code.")
            raise psycopg2.InterfaceError("No active database connection for insertion.")

        try:
            columns = product_data.keys()
            values = [product_data[col] for col in columns]

            insert_query = sql.SQL(
                "INSERT INTO products ({}) VALUES ({}) "
                "ON CONFLICT (url) DO UPDATE SET {}"
            ).format(
                sql.SQL(', ').join(map(sql.Identifier, columns)),
                sql.SQL(', ').join(sql.Placeholder() * len(columns)),
                sql.SQL(', ').join(
                    sql.SQL("{} = {}").format(sql.Identifier(col), sql.Placeholder())
                    for col in columns if col != 'url'
                )
            )

            self.cur.execute(insert_query, values + [product_data[col] for col in columns if col != 'url'])
            # IMPORTANT: DO NOT COMMIT HERE. The context manager will commit all transactions at once.
            logger.debug(f"Prepared insert for '{product_data.get('product_name', 'Unknown')}' (will commit later).")
        except psycopg2.Error as e:
            logger.error(f"✗ Database error during insertion for {product_data.get('url', 'Unknown URL')}: {e}")
            # Do not rollback here either. Let the context manager handle the overall transaction rollback if needed.
            raise
        except Exception as e:
            logger.error(f"✗ Unexpected error during database insertion for {product_data.get('url', 'Unknown URL')}: {e}")
            raise
        # No finally block for disconnect/commit here, as connection is managed by __enter__/__exit__


    def __enter__(self):
        """
        Connects to the database when entering the 'with' block.
        """
        self._connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Commits/rolls back transactions and closes the connection when exiting the 'with' block.
        """
        if exc_type: # An exception occurred within the 'with' block
            if self.conn:
                self.conn.rollback() # Rollback all operations in this transaction
                logger.error(f"✗ Transaction rolled back due to exception: {exc_val}")
        elif self.conn:
            self.conn.commit() # Commit all successful operations in this transaction
            logger.info("✓ Transaction committed successfully.")
        
        self._disconnect() # Always disconnect on exit from the 'with' block