from mysql.connector import connect, Error

class DataCollectorCommandHandler:
    def __init__(self, db_config):
        self.db_config = db_config

    def update_or_insert_stock(self, ticker, value):
        """
        Inserisce o aggiorna il valore del ticker nella tabella stock_data.
        """
        try:
            with connect(**self.db_config) as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO stock_data (ticker, value)
                        VALUES (%s, %s)
                        ON DUPLICATE KEY UPDATE value = VALUES(value), timestamp = CURRENT_TIMESTAMP
                        """,
                        (ticker, value)
                    )
                    connection.commit()
        except Error as e:
            print(f"Errore durante l'aggiornamento del ticker {ticker}: {e}")
            raise