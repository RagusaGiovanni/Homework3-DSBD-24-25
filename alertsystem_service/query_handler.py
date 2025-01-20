from mysql.connector import connect, Error

class AlertQueryHandler:
    def __init__(self, db_config):
        self.db_config = db_config

    def get_user_thresholds_and_email(self, ticker):
        """
        Recupera le soglie (high_value, low_value) e l'email associata a un ticker dal database.
        """
        try:
            with connect(**self.db_config) as connection:
                with connection.cursor(dictionary=True) as cursor:
                    cursor.execute("""
                        SELECT u.email, u.high_value, u.low_value
                        FROM users u
                        JOIN user_tickers t ON u.id = t.user_id
                        WHERE t.ticker = %s
                    """, (ticker,))
                    result = cursor.fetchone()
                    return result  # Restituisce un dizionario con email, high_value e low_value
        except Error as e:
            print(f"Errore durante la query per il ticker {ticker}: {e}")
            raise