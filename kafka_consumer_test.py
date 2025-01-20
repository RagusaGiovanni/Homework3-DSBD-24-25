from confluent_kafka import Consumer, KafkaException, KafkaError
import json

# Configurazione del Kafka consumer
kafka_config = {
    'bootstrap.servers': 'localhost:9092',  # Assicurati che il nome del servizio sia corretto
    'group.id': 'test-consumer-group',
    'auto.offset.reset': 'earliest'  # Legge i messaggi dall'inizio del topic
}

def consume_test_messages():
    """ Consuma i messaggi dal topic 'user-events' """
    consumer = Consumer(kafka_config)
    topic = "user-events"

    # Iscriviti al topic
    consumer.subscribe([topic])

    print("Inizio consumo dei messaggi...")
    try:
        while True:
            msg = consumer.poll(timeout=10.0)  # Timeout per evitare il blocco infinito
            if msg is None:
                print("Nessun messaggio ricevuto...")
                continue
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    print("Fine della partizione raggiunta.")
                else:
                    raise KafkaException(msg.error())
            else:
                # Decodifica e stampa il messaggio ricevuto
                message = json.loads(msg.value().decode('utf-8'))
                print(f"Messaggio ricevuto: {message}")

    except KeyboardInterrupt:
        print("Chiusura del consumer...")
    finally:
        consumer.close()

if __name__ == "__main__":
    consume_test_messages()