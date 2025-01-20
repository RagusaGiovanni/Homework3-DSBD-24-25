from mysql.connector import connect, Error

class StockQueryHandler:
    def __init__(self, db_config=None):
        self.db_config = db_config or {
            "host": "mysql_db",
            "user": "root",
            "password": "example",
            "database": "finance_data"
        }

    def get_user_id_by_email(self, email):
        """
        Recupera l'ID utente utilizzando l'email.
        """
        try:
            with connect(**self.db_config) as connection:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT id FROM users WHERE email=%s", (email,))
                    return cursor.fetchone()
        except Error as e:
            print(f"Errore durante il recupero dell'utente per email {email}: {e}")
            raise

    def check_ticker_exists_for_user(self, user_id, ticker):
        """
        Verifica se un ticker esiste per un determinato utente.
        """
        try:
            with connect(**self.db_config) as connection:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT id FROM user_tickers WHERE user_id=%s AND ticker=%s", (user_id, ticker))
                    return cursor.fetchone()
        except Error as e:
            print(f"Errore durante la verifica del ticker {ticker} per utente {user_id}: {e}")
            raise

    def get_latest_stock_value(self, ticker):
        """
        Recupera il valore più recente del ticker.
        """
        try:
            with connect(**self.db_config) as connection:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT value FROM stock_data WHERE ticker=%s ORDER BY timestamp DESC LIMIT 1", (ticker,))
                    return cursor.fetchone()
        except Error as e:
            print(f"Errore durante il recupero del valore più recente per il ticker {ticker}: {e}")
            raise

    def calculate_average_stock_value(self, ticker, count):
        """
        Calcola la media degli ultimi X valori di un ticker.
        """
        try:
            with connect(**self.db_config) as connection:
                with connection.cursor() as cursor:
                    cursor.execute("""
                        SELECT AVG(value) 
                        FROM (SELECT value FROM stock_data WHERE ticker=%s ORDER BY timestamp DESC LIMIT %s) as subquery
                    """, (ticker, count))
                    return cursor.fetchone()
        except Error as e:
            print(f"Errore durante il calcolo della media per il ticker {ticker}: {e}")
            raise