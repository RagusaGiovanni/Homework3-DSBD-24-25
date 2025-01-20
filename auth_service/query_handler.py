from mysql.connector import connect, Error


class UserQueryHandler:
    def __init__(self, db_config=None):
        self.db_config = db_config or {
            "host": "mysql_db",
            "user": "root",
            "password": "example",
            "database": "finance_data"
        }

    def get_user_by_email(self, email: str) -> dict:
        """
        Ottiene un utente dal database utilizzando l'email.
        Restituisce un dizionario con id, high_value e low_value.
        """
        try:
            with connect(**self.db_config) as connection:
                with connection.cursor(dictionary=True) as cursor:
                    cursor.execute(
                        "SELECT id, high_value, low_value FROM users WHERE email = %s",
                        (email,)
                    )
                    result = cursor.fetchone()
                    return result
        except Error as e:
            print(f"Errore durante la lettura dell'utente con email {email}: {e}")
            raise

    def get_ticker_for_user(self, user_id: int, ticker: str) -> dict:
        """
        Ottiene un ticker associato a un utente.
        Restituisce un dizionario con i dettagli del ticker.
        """
        try:
            with connect(**self.db_config) as connection:
                with connection.cursor(dictionary=True) as cursor:
                    cursor.execute(
                        "SELECT id, ticker FROM user_tickers WHERE user_id = %s AND ticker = %s",
                        (user_id, ticker)
                    )
                    result = cursor.fetchone()
                    return result
        except Error as e:
            print(f"Errore durante la lettura del ticker {ticker} per utente {user_id}: {e}")
            raise