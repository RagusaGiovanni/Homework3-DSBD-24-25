from mysql.connector import connect, Error


class UserCommandHandler:
    def __init__(self, db_config=None):
        self.db_config = db_config or {
            "host": "mysql_db",
            "user": "root",
            "password": "example",
            "database": "finance_data"
        }

    def create_user(self, email: str, high_value: float, low_value: float) -> int:
        """
        Crea un nuovo utente nel database e restituisce l'ID dell'utente creato.
        """
        try:
            with connect(**self.db_config) as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        "INSERT INTO users (email, high_value, low_value) VALUES (%s, %s, %s)",
                        (email, high_value, low_value)
                    )
                    connection.commit()
                    return cursor.lastrowid
        except Error as e:
            print(f"Errore durante la creazione dell'utente con email {email}: {e}")
            raise

    def add_ticker(self, user_id: int, ticker: str) -> None:
        """
        Aggiunge un ticker associato a un utente.
        """
        try:
            with connect(**self.db_config) as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        "INSERT INTO user_tickers (user_id, ticker) VALUES (%s, %s)",
                        (user_id, ticker)
                    )
                    connection.commit()
        except Error as e:
            print(f"Errore durante l'aggiunta del ticker {ticker} per utente {user_id}: {e}")
            raise

    def update_ticker(self, user_id: int, old_ticker: str, new_ticker: str) -> None:
        """
        Aggiorna il ticker associato a un utente.
        """
        try:
            with connect(**self.db_config) as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        "UPDATE user_tickers SET ticker = %s WHERE user_id = %s AND ticker = %s",
                        (new_ticker, user_id, old_ticker)
                    )
                    connection.commit()
        except Error as e:
            print(f"Errore durante l'aggiornamento del ticker da {old_ticker} a {new_ticker} per utente {user_id}: {e}")
            raise

    def update_thresholds(self, user_id: int, high_value: float, low_value: float) -> None:
        """
        Aggiorna le soglie di un utente.
        """
        try:
            with connect(**self.db_config) as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        "UPDATE users SET high_value = %s, low_value = %s WHERE id = %s",
                        (high_value, low_value, user_id)
                    )
                    connection.commit()
        except Error as e:
            print(f"Errore durante l'aggiornamento delle soglie per utente {user_id}: {e}")
            raise

    def delete_ticker(self, user_id: int, ticker: str) -> None:
        """
        Elimina un ticker associato a un utente.
        """
        try:
            with connect(**self.db_config) as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        "DELETE FROM user_tickers WHERE user_id = %s AND ticker = %s",
                        (user_id, ticker)
                    )
                    connection.commit()
        except Error as e:
            print(f"Errore durante l'eliminazione del ticker {ticker} per utente {user_id}: {e}")
            raise

    def delete_user(self, user_id: int) -> None:
        """
        Elimina un utente e tutti i suoi ticker.
        """
        try:
            with connect(**self.db_config) as connection:
                with connection.cursor() as cursor:
                    cursor.execute("DELETE FROM user_tickers WHERE user_id = %s", (user_id,))
                    cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
                    connection.commit()
        except Error as e:
            print(f"Errore durante l'eliminazione dell'utente {user_id}: {e}")
            raise