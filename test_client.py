import grpc
import proxy_pb2
import proxy_pb2_grpc
import time
import random
import yfinance as yf


def get_random_ticker():
    """
    Ottieni un ticker casuale da una lista predefinita o da yfinance.
    """
    tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "META", "NVDA", "NFLX", "ADBE", "INTC"]
    return random.choice(tickers)


def get_random_thresholds():
    """
    Genera valori casuali per le soglie high_value e low_value.
    """
    low_value = round(random.uniform(50, 200), 2)  # Genera un valore tra 50 e 200
    high_value = round(low_value + random.uniform(20, 100), 2)  # high_value > low_value
    return low_value, high_value


def run():
    try:
        # Connessione al Proxy Service
        with grpc.insecure_channel('localhost:5005') as proxy_channel:
            proxy_stub = proxy_pb2_grpc.ProxyServiceStub(proxy_channel)

            # Lista di utenti e ticker per test
            utenti = [
                {"email": "user1@example.com", "tickers": ["AAPL", "GOOGL", "AMZN"]},
                {"email": "user2@example.com", "tickers": ["MSFT", "TSLA", "NFLX"]},
                {"email": "user3@example.com", "tickers": ["META", "NVDA", "ADBE"]}
            ]

            # --- AUTH Service Tests ---
            print("\n--- AUTH Service Tests ---")
            for utente in utenti:
                # Registra l'utente con soglie casuali
                print(f"\n--- Test: RegisterUser for {utente['email']} ---")
                low_value, high_value = get_random_thresholds()
                response = proxy_stub.ForwardRequest(proxy_pb2.ProxyUserRequest(
                    service="auth_service",
                    method="RegisterUser",
                    email=utente["email"],
                    ticker="",  # Nessun ticker associato in questa chiamata
                    high_value=high_value,
                    low_value=low_value
                ))
                print(f"RegisterUser Response: {response.status} (High: {high_value}, Low: {low_value})")

                # Registra i ticker associati all'utente
                for ticker in utente["tickers"]:
                    print(f"\n--- Test: RegisterTicker for {utente['email']} with ticker {ticker} ---")
                    response = proxy_stub.ForwardRequest(proxy_pb2.ProxyUserRequest(
                        service="auth_service",
                        method="RegisterUser",
                        email=utente["email"],
                        ticker=ticker
                    ))
                    print(f"RegisterTicker Response: {response.status}")

            # Aggiorna le soglie degli utenti
            print("\n--- Test: UpdateThresholds ---")
            for utente in utenti:
                print(f"\n--- Test: UpdateThresholds for {utente['email']} ---")
                new_low_value, new_high_value = get_random_thresholds()
                response = proxy_stub.ForwardRequest(proxy_pb2.ProxyUserRequest(
                    service="auth_service",
                    method="UpdateThresholds",
                    email=utente["email"],
                    low_value=new_low_value,
                    high_value=new_high_value
                ))
                print(f"UpdateThresholds Response: {response.status} (High: {new_high_value}, Low: {new_low_value})")

            # Aggiorna i ticker degli utenti esistenti
            print("\n--- Test: UpdateUser ---")
            for utente in utenti:
                print(f"\n--- Test: UpdateUser for {utente['email']} ---")
                old_ticker = utente["tickers"][0]  # Prendi il primo ticker associato all'utente

                # Trova un nuovo ticker che non sia già associato all'utente
                new_ticker = get_random_ticker()
                while new_ticker in utente["tickers"]:
                    new_ticker = get_random_ticker()

                response = proxy_stub.ForwardRequest(proxy_pb2.ProxyUserRequest(
                    service="auth_service",
                    method="UpdateUser",
                    email=utente["email"],
                    old_ticker=old_ticker,
                    new_ticker=new_ticker,
                    high_value=None,  # Specifica `None` per non aggiornare soglie
                    low_value=None
                ))
                print(f"UpdateUser Response: {response.status}")

                if response.status == "User and thresholds updated successfully":
                    # Aggiorna la lista locale dei ticker
                    utente["tickers"][0] = new_ticker  # Sostituisci il vecchio ticker con il nuovo
                    print(f"Ticker aggiornato per {utente['email']}: {old_ticker} -> {new_ticker}")

            # Attendi che il DataCollector aggiorni i dati
            print("\nAspetto che il DataCollector aggiorni la tabella stock_data...")
            time.sleep(25)  # Assicurati di attendere più del ciclo del DataCollector

            # --- Stock Management Service Tests ---
            print("\n--- Stock Management Service Tests ---")
            for utente in utenti:
                for ticker in utente["tickers"]:
                    print(f"\n--- Test: GetStock for {utente['email']} and ticker {ticker} ---")
                    response = proxy_stub.ForwardRequest(proxy_pb2.ProxyUserRequest(
                        service="stock_service",
                        method="GetStock",
                        email=utente["email"],
                        ticker=ticker
                    ))
                    if response.status == "Stock found":
                        print(f"GetStock Response: Status={response.status}, Value={response.value}")
                    else:
                        print(f"GetStock Response: Status={response.status}")

                for ticker in utente["tickers"]:
                    print(f"\n--- Test: GetAverage for ticker {ticker} of user {utente['email']} ---")
                    response = proxy_stub.ForwardRequest(proxy_pb2.ProxyUserRequest(
                        service="stock_service",
                        method="GetAverage",
                        email=utente["email"],
                        ticker=ticker,
                        count=5
                    ))
                    if response.status == "Average calculated":
                        print(f"GetAverage Response: Status={response.status}, Average={response.average}")
                    else:
                        print(f"GetAverage Response: Status={response.status}")

            # Elimina utenti e i loro ticker
            print("\n--- Test: DeleteUser ---")
            for utente in utenti:
                print(f"\n--- Test: DeleteUser for {utente['email']} ---")
                response = proxy_stub.ForwardRequest(proxy_pb2.ProxyUserRequest(
                    service="auth_service",
                    method="DeleteUser",
                    email=utente["email"]
                ))
                print(f"DeleteUser Response: {response.status}")

    except grpc.RpcError as e:
        print(f"Errore gRPC: {e.code()} - {e.details()}")


if __name__ == "__main__":
    run()