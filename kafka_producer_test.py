from confluent_kafka import Producer
import json

# Configurazione del Kafka producer
kafka_config = {
    'bootstrap.servers': 'localhost:9092',  # Assicurati che il nome del servizio sia corretto dal docker-compose
    'client.id': 'test-producer'
}

def delivery_report(err, msg):
    """ Callback che conferma se il messaggio è stato inviato con successo """
    if err is not None:
        print(f"Errore nell'invio del messaggio: {err}")
    else:
        print(f"Messaggio inviato a {msg.topic()} [{msg.partition()}] con offset {msg.offset()}")

def send_test_message():
    """ Invia un messaggio di prova a Kafka """
    producer = Producer(kafka_config)
    topic = "user-events"

    # Crea un messaggio di prova
    test_message = {
        "type": "TEST_EVENT",
        "email": "test@example.com",
        "message": "Questo è un messaggio di test per Kafka"
    }

    print("Invio del messaggio...")
    producer.produce(topic, key=test_message["email"], value=json.dumps(test_message), callback=delivery_report)

    # Aspetta che il messaggio venga inviato
    producer.flush()

if __name__ == "__main__":
    send_test_message()