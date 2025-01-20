from concurrent import futures
import grpc
import auth_pb2
import auth_pb2_grpc
from confluent_kafka import Producer
import json
from command_handler import UserCommandHandler
from query_handler import UserQueryHandler
from prometheus_client import start_http_server, Counter, Histogram, Gauge
import time

# Configurazione del Producer Kafka
kafka_config = {
    'bootstrap.servers': 'kafka:9092',
    'client.id': 'auth-service-producer'
}
producer = Producer(kafka_config)

# Prometheus metrics
REQUEST_COUNTER = Counter('auth_service_requests_total', 'Total number of requests', ['method', 'status'])
REQUEST_DURATION = Histogram('auth_service_request_duration_seconds', 'Request duration in seconds', ['method'])
DATABASE_LATENCY = Gauge('auth_service_database_latency_seconds', 'Database latency in seconds')

# Funzione per inviare eventi Kafka
def send_event_to_kafka(event_type, payload):
    topic = "user-events"
    message = {"type": event_type, **payload}
    producer.produce(topic, key=payload.get("email", ""), value=json.dumps(message), callback=delivery_report)
    producer.flush()

# Callback per la verifica della consegna
def delivery_report(err, msg):
    if err is not None:
        print(f"Errore nell'invio del messaggio Kafka: {err}")
    else:
        print(f"Messaggio inviato al topic {msg.topic()} - Chiave: {msg.key()} - Valore: {msg.value()}")

class AuthService(auth_pb2_grpc.AuthServiceServicer):
    def __init__(self):
        self.command_handler = UserCommandHandler()
        self.query_handler = UserQueryHandler()

    def RegisterUser(self, request, context):
        start_time = time.time()
        REQUEST_COUNTER.labels(method='RegisterUser', status='started').inc()
        try:
            db_start_time = time.time()
            user = self.query_handler.get_user_by_email(request.email)
            DATABASE_LATENCY.set(time.time() - db_start_time)

            if user:
                user_id = user['id']
            else:
                db_start_time = time.time()
                user_id = self.command_handler.create_user(request.email, request.high_value, request.low_value)
                DATABASE_LATENCY.set(time.time() - db_start_time)
                send_event_to_kafka("UserRegistered", {
                    "email": request.email,
                    "high_value": request.high_value,
                    "low_value": request.low_value
                })
                print(f"Utente {request.email} registrato con ID {user_id}")

            if request.ticker:
                db_start_time = time.time()
                existing_ticker = self.query_handler.get_ticker_for_user(user_id, request.ticker)
                DATABASE_LATENCY.set(time.time() - db_start_time)

                if existing_ticker:
                    REQUEST_COUNTER.labels(method='RegisterUser', status='ticker_exists').inc()
                    return auth_pb2.AuthUserResponse(status="Ticker already exists for user")

                db_start_time = time.time()
                self.command_handler.add_ticker(user_id, request.ticker)
                DATABASE_LATENCY.set(time.time() - db_start_time)

                send_event_to_kafka("TickerRegistered", {"email": request.email, "ticker": request.ticker})
                print(f"Ticker {request.ticker} associato all'utente {request.email}")

            REQUEST_COUNTER.labels(method='RegisterUser', status='success').inc()
            REQUEST_DURATION.labels(method='RegisterUser').observe(time.time() - start_time)
            return auth_pb2.AuthUserResponse(status="User and ticker registered successfully")
        except Exception as e:
            REQUEST_COUNTER.labels(method='RegisterUser', status='error').inc()
            print(f"Errore durante la registrazione dell'utente: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            return auth_pb2.AuthUserResponse(status="Internal server error")

    def UpdateUser(self, request, context):
        start_time = time.time()
        REQUEST_COUNTER.labels(method='UpdateUser', status='started').inc()
        try:
            db_start_time = time.time()
            user = self.query_handler.get_user_by_email(request.email)
            DATABASE_LATENCY.set(time.time() - db_start_time)

            if not user:
                REQUEST_COUNTER.labels(method='UpdateUser', status='not_found').inc()
                context.set_code(grpc.StatusCode.NOT_FOUND)
                return auth_pb2.AuthUserResponse(status="User not found")
            user_id = user['id']

            if request.old_ticker and request.new_ticker:
                db_start_time = time.time()
                old_ticker_exists = self.query_handler.get_ticker_for_user(user_id, request.old_ticker)
                DATABASE_LATENCY.set(time.time() - db_start_time)

                if not old_ticker_exists:
                    REQUEST_COUNTER.labels(method='UpdateUser', status='old_ticker_not_found').inc()
                    context.set_code(grpc.StatusCode.NOT_FOUND)
                    return auth_pb2.AuthUserResponse(status="Old ticker not found")

                db_start_time = time.time()
                self.command_handler.update_ticker(user_id, request.old_ticker, request.new_ticker)
                DATABASE_LATENCY.set(time.time() - db_start_time)

                send_event_to_kafka("TickerUpdated", {
                    "email": request.email,
                    "old_ticker": request.old_ticker,
                    "new_ticker": request.new_ticker
                })
                print(f"Ticker aggiornato per utente {request.email}: {request.old_ticker} -> {request.new_ticker}")

            if request.high_value or request.low_value:
                db_start_time = time.time()
                self.command_handler.update_thresholds(user_id, request.high_value, request.low_value)
                DATABASE_LATENCY.set(time.time() - db_start_time)

                send_event_to_kafka("ThresholdsUpdated", {
                    "email": request.email,
                    "high_value": request.high_value,
                    "low_value": request.low_value
                })
                print(f"Soglie aggiornate per utente {request.email}: High={request.high_value}, Low={request.low_value}")

            REQUEST_COUNTER.labels(method='UpdateUser', status='success').inc()
            REQUEST_DURATION.labels(method='UpdateUser').observe(time.time() - start_time)
            return auth_pb2.AuthUserResponse(status="User and thresholds updated successfully")
        except Exception as e:
            REQUEST_COUNTER.labels(method='UpdateUser', status='error').inc()
            print(f"Errore durante l'aggiornamento dell'utente: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            return auth_pb2.AuthUserResponse(status="Internal server error")

    def UpdateThresholds(self, request, context):
        start_time = time.time()
        REQUEST_COUNTER.labels(method='UpdateThresholds', status='started').inc()
        try:
            db_start_time = time.time()
            user = self.query_handler.get_user_by_email(request.email)
            DATABASE_LATENCY.set(time.time() - db_start_time)

            if not user:
                REQUEST_COUNTER.labels(method='UpdateThresholds', status='not_found').inc()
                context.set_code(grpc.StatusCode.NOT_FOUND)
                return auth_pb2.AuthUserResponse(status="User not found")
            user_id = user['id']

            db_start_time = time.time()
            self.command_handler.update_thresholds(user_id, request.high_value, request.low_value)
            DATABASE_LATENCY.set(time.time() - db_start_time)

            send_event_to_kafka("ThresholdsUpdated", {
                "email": request.email,
                "high_value": request.high_value,
                "low_value": request.low_value
            })
            print(f"Soglie aggiornate per utente {request.email}: High={request.high_value}, Low={request.low_value}")

            REQUEST_COUNTER.labels(method='UpdateThresholds', status='success').inc()
            REQUEST_DURATION.labels(method='UpdateThresholds').observe(time.time() - start_time)
            return auth_pb2.AuthUserResponse(status="Thresholds updated successfully")
        except Exception as e:
            REQUEST_COUNTER.labels(method='UpdateThresholds', status='error').inc()
            print(f"Errore durante l'aggiornamento delle soglie: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            return auth_pb2.AuthUserResponse(status="Internal server error")

    def DeleteUser(self, request, context):
        """
        Elimina un utente o un ticker associato.
        """
        start_time = time.time()
        REQUEST_COUNTER.labels(method='DeleteUser', status='started').inc()
        try:
            # Recupera l'utente
            db_start_time = time.time()
            user = self.query_handler.get_user_by_email(request.email)
            DATABASE_LATENCY.set(time.time() - db_start_time)

            if not user:
                REQUEST_COUNTER.labels(method='DeleteUser', status='not_found').inc()
                context.set_code(grpc.StatusCode.NOT_FOUND)
                return auth_pb2.AuthUserResponse(status="User not found")
            user_id = user['id']

            # Elimina un ticker specifico o tutto l'utente
            if request.ticker:
                db_start_time = time.time()
                self.command_handler.delete_ticker(user_id, request.ticker)
                DATABASE_LATENCY.set(time.time() - db_start_time)
                send_event_to_kafka("TickerDeleted", {"email": request.email, "ticker": request.ticker})
                print(f"Ticker {request.ticker} eliminato per utente {request.email}")
                REQUEST_COUNTER.labels(method='DeleteUser', status='success').inc()
                REQUEST_DURATION.labels(method='DeleteUser').observe(time.time() - start_time)
                return auth_pb2.AuthUserResponse(status="Ticker deleted successfully")
            else:
                db_start_time = time.time()
                self.command_handler.delete_user(user_id)
                DATABASE_LATENCY.set(time.time() - db_start_time)
                send_event_to_kafka("UserDeleted", {"email": request.email})
                print(f"Utente {request.email} eliminato con tutti i suoi ticker")
                REQUEST_COUNTER.labels(method='DeleteUser', status='success').inc()
                REQUEST_DURATION.labels(method='DeleteUser').observe(time.time() - start_time)
                return auth_pb2.AuthUserResponse(status="User and associated tickers deleted successfully")
        except Exception as e:
            REQUEST_COUNTER.labels(method='DeleteUser', status='error').inc()
            print(f"Errore durante l'eliminazione dell'utente: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            return auth_pb2.AuthUserResponse(status="Internal server error")

def serve():
    start_http_server(8000)  # Porta per le metriche
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    auth_pb2_grpc.add_AuthServiceServicer_to_server(AuthService(), server)
    server.add_insecure_port('0.0.0.0:5001')
    server.start()
    print("AuthService in esecuzione sulla porta 5001 con metriche esposte su 8000...")
    server.wait_for_termination()

if __name__ == '__main__':
    serve()