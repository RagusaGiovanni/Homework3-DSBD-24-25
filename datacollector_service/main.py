import os
import time
import grpc
import yfinance as yf
import mysql.connector
from concurrent import futures
from pybreaker import CircuitBreaker
from prometheus_client import start_http_server, Counter, Gauge
from confluent_kafka import Producer
import json
import datacollector_pb2
import datacollector_pb2_grpc
from command_handler import DataCollectorCommandHandler
from query_handler import DataCollectorQueryHandler

# Configurazione del database
db_config = {
    'host': 'mysql_db',
    'user': 'root',
    'password': 'example',
    'database': 'finance_data',
    'connect_timeout': 10  # Timeout per evitare blocchi prolungati
}

# Configurazione del Circuit Breaker
breaker = CircuitBreaker(fail_max=3, reset_timeout=60)

# Configurazione del Producer Kafka
kafka_config = {
    'bootstrap.servers': 'kafka:9092',  # Indirizzo del broker Kafka
    'client.id': 'data-collector-producer'  # Identificativo del client Kafka
}
producer = Producer(kafka_config)

# Prometheus Metrics
TICKER_COLLECTION_COUNTER = Counter('datacollector_ticker_collections_total', 
                                    'Total number of ticker collections completed')

ACTIVE_TICKERS_GAUGE = Gauge('datacollector_active_tickers', 
                             'Number of active tickers currently being monitored')

# Funzione per inviare eventi Kafka
def send_event_to_kafka(event_type, payload):
    """
    Invia un evento Kafka al topic 'to-alert-system'.
    """
    try:
        topic = "to-alert-system"
        message = {"type": event_type, **payload}
        producer.produce(topic, value=json.dumps(message), callback=delivery_report)
        producer.flush()
    except Exception as e:
        print(f"Errore nell'invio del messaggio Kafka: {e}")


def delivery_report(err, msg):
    """
    Callback che verifica lo stato di consegna del messaggio Kafka.
    """
    if err is not None:
        print(f"Errore nell'invio del messaggio Kafka: {err}")
    else:
        print(f"Messaggio inviato al topic {msg.topic()} - Valore: {msg.value()}")


class DataCollectorService(datacollector_pb2_grpc.DataCollectorServiceServicer):
    def __init__(self):
        self.command_handler = DataCollectorCommandHandler(db_config)
        self.query_handler = DataCollectorQueryHandler(db_config)

    @breaker
    def get_stock_value(self, ticker):
        """
        Recupera il valore corrente del ticker da Yahoo Finance.
        """
        try:
            stock = yf.Ticker(ticker)
            value = (
                stock.info.get('regularMarketPrice')
                or stock.info.get('previousClose')
                or stock.info.get('ask')
            )
            if value is None:
                data = stock.history(period="1d")
                if not data.empty:
                    value = data['Close'].iloc[-1]
            return value
        except Exception as e:
            print(f"Errore nel recupero dei dati per {ticker}: {e}")
            return None

    def collect_stock_data_internal(self):
        """
        Logica per raccogliere i dati sui ticker registrati e inserirli nel database.
        """
        collected_count = 0
        try:
            tickers = self.query_handler.get_all_tickers()
            ACTIVE_TICKERS_GAUGE.set(len(tickers))  # Aggiorna la metrica con il numero di ticker attivi
            print(f"Tickers trovati: {tickers}")

            for ticker in tickers:
                try:
                    stock_value = self.get_stock_value(ticker)
                    if stock_value is not None:
                        print(f"Aggiornamento per {ticker}: valore={stock_value}")
                        self.command_handler.update_or_insert_stock(ticker, stock_value)
                        collected_count += 1

                        # Invia un evento Kafka per ciascun ticker aggiornato
                        send_event_to_kafka("StockUpdated", {"ticker": ticker, "value": stock_value})

                except Exception as e:
                    print(f"Errore durante l'aggiornamento per {ticker}: {e}")

            # Aggiorna il COUNTER per le collezioni completate
            TICKER_COLLECTION_COUNTER.inc()

            # Invia evento Kafka finale solo se ci sono stati aggiornamenti
            if collected_count > 0:
                send_event_to_kafka("UpdateCompleted", {"status": "success", "updated_count": collected_count})
            else:
                print("Nessun aggiornamento effettuato. Nessun messaggio inviato a Kafka.")

        except Exception as e:
            print(f"Errore durante la raccolta dati: {e}")
            raise

        return collected_count

    def CollectStockData(self, request, context):
        """
        Metodo gRPC per raccogliere i dati sui ticker.
        """
        try:
            collected_count = self.collect_stock_data_internal()
            return datacollector_pb2.CollectionResponse(
                status="Data collection completed successfully",
                collected=collected_count
            )
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return datacollector_pb2.CollectionResponse(
                status="Error during data collection",
                collected=0
            )

    def start_continuous_collection(self, interval=10):
        """
        Avvia un ciclo continuo per raccogliere i dati sui ticker a intervalli regolari.
        """
        print("Attesa per inizializzare il ciclo continuo...")
        time.sleep(10)  # Ritardo iniziale per garantire che il database sia pronto

        while True:
            try:
                print("Avvio della raccolta automatica...")
                self.collect_stock_data_internal()
            except Exception as e:
                print(f"Errore durante la raccolta automatica: {e}")
            finally:
                time.sleep(interval)  # Attendi l'intervallo specificato


def serve():
    """
    Avvia il server gRPC e il ciclo continuo.
    """
    start_http_server(8001)  # Porta per le metriche Prometheus
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    service = DataCollectorService()

    # Registra il servizio gRPC
    datacollector_pb2_grpc.add_DataCollectorServiceServicer_to_server(service, server)
    server.add_insecure_port('0.0.0.0:5004')

    # Avvia il ciclo continuo in un thread separato
    executor = futures.ThreadPoolExecutor(max_workers=1)
    executor.submit(service.start_continuous_collection, interval=10)

    server.start()
    print("DataCollector Service in esecuzione sulla porta 5004 con metriche su 8001...")
    server.wait_for_termination()


if __name__ == '__main__':
    serve()