from concurrent import futures
import grpc
import stock_pb2
import stock_pb2_grpc
from query_handler import StockQueryHandler
from prometheus_client import start_http_server, Counter, Gauge
import time

# Configurazione del database
db_config = {
    'host': 'mysql_db',
    'user': 'root',
    'password': 'example',
    'database': 'finance_data'
}

# Prometheus Metrics
REQUEST_COUNTER = Counter(
    'stock_service_requests_total', 
    'Total number of requests', 
    ['method', 'status']
)

ACTIVE_USERS_GAUGE = Gauge(
    'stock_service_active_users', 
    'Number of unique users actively requesting data'
)

class StockService(stock_pb2_grpc.StockServiceServicer):
    def __init__(self):
        self.query_handler = StockQueryHandler(db_config)
        self.active_users = set()  # Per monitorare utenti attivi unici

    def GetStock(self, request, context):
        start_time = time.time()
        REQUEST_COUNTER.labels(method='GetStock', status='started').inc()
        try:
            # Recupera l'ID utente
            user = self.query_handler.get_user_id_by_email(request.email)
            if not user:
                REQUEST_COUNTER.labels(method='GetStock', status='user_not_found').inc()
                context.set_code(grpc.StatusCode.NOT_FOUND)
                return stock_pb2.StockResponse(status="User not found")
            user_id = user[0]

            # Aggiorna gli utenti attivi
            self.active_users.add(request.email)
            ACTIVE_USERS_GAUGE.set(len(self.active_users))

            # Verifica se il ticker esiste
            ticker_exists = self.query_handler.check_ticker_exists_for_user(user_id, request.ticker)
            if not ticker_exists:
                REQUEST_COUNTER.labels(method='GetStock', status='ticker_not_found').inc()
                context.set_code(grpc.StatusCode.NOT_FOUND)
                return stock_pb2.StockResponse(status="Ticker not found for this user")

            # Recupera il valore più recente del ticker
            latest_value = self.query_handler.get_latest_stock_value(request.ticker)
            if latest_value:
                REQUEST_COUNTER.labels(method='GetStock', status='success').inc()
                return stock_pb2.StockResponse(status="Stock found", value=latest_value[0])
            else:
                REQUEST_COUNTER.labels(method='GetStock', status='stock_not_found').inc()
                context.set_code(grpc.StatusCode.NOT_FOUND)
                return stock_pb2.StockResponse(status="Stock not found")
        except Exception as e:
            REQUEST_COUNTER.labels(method='GetStock', status='error').inc()
            print(f"Errore durante GetStock: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            return stock_pb2.StockResponse(status="Internal server error")
        finally:
            self.cleanup_active_users(request.email)

    def GetAverage(self, request, context):
        start_time = time.time()
        REQUEST_COUNTER.labels(method='GetAverage', status='started').inc()
        try:
            # Recupera l'ID utente
            user = self.query_handler.get_user_id_by_email(request.email)
            if not user:
                REQUEST_COUNTER.labels(method='GetAverage', status='user_not_found').inc()
                context.set_code(grpc.StatusCode.NOT_FOUND)
                return stock_pb2.AverageResponse(status="User not found")
            user_id = user[0]

            # Aggiorna gli utenti attivi
            self.active_users.add(request.email)
            ACTIVE_USERS_GAUGE.set(len(self.active_users))

            # Verifica se il ticker esiste
            ticker_exists = self.query_handler.check_ticker_exists_for_user(user_id, request.ticker)
            if not ticker_exists:
                REQUEST_COUNTER.labels(method='GetAverage', status='ticker_not_found').inc()
                context.set_code(grpc.StatusCode.NOT_FOUND)
                return stock_pb2.AverageResponse(status="Ticker not found for this user")

            # Calcola la media
            average_value = self.query_handler.calculate_average_stock_value(request.ticker, request.count)
            if average_value and average_value[0] is not None:
                REQUEST_COUNTER.labels(method='GetAverage', status='success').inc()
                return stock_pb2.AverageResponse(status="Average calculated", average=average_value[0])
            else:
                REQUEST_COUNTER.labels(method='GetAverage', status='insufficient_data').inc()
                context.set_code(grpc.StatusCode.NOT_FOUND)
                return stock_pb2.AverageResponse(status="Stock not found or insufficient data")
        except Exception as e:
            REQUEST_COUNTER.labels(method='GetAverage', status='error').inc()
            print(f"Errore durante GetAverage: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            return stock_pb2.AverageResponse(status="Internal server error")
        finally:
            self.cleanup_active_users(request.email)

    def cleanup_active_users(self, email):
        """
        Rimuove l'utente attivo dalla metrica se non ha richieste in corso.
        """
        if email in self.active_users:
            self.active_users.remove(email)
        ACTIVE_USERS_GAUGE.set(len(self.active_users))

def serve():
    start_http_server(8002)  # Porta per le metriche Prometheus
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    stock_pb2_grpc.add_StockServiceServicer_to_server(StockService(), server)
    server.add_insecure_port('0.0.0.0:5002')
    server.start()
    print("Stock Service in esecuzione sulla porta 5002 con metriche su 8002...")
    server.wait_for_termination()

if __name__ == '__main__':
    serve()