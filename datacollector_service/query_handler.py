from mysql.connector import connect, Error

class DataCollectorQueryHandler:
    def __init__(self, db_config):
        self.db_config = db_config

    def get_all_tickers(self):
        """
        Recupera tutti i ticker univoci dalla tabella user_tickers.
        """
        try:
            with connect(**self.db_config) as connection:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT DISTINCT ticker FROM user_tickers")
                    return [row[0] for row in cursor.fetchall()]
        except Error as e:
            print(f"Errore durante il recupero dei ticker: {e}")
            raise