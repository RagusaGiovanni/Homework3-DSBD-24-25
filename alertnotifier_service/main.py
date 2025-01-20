from confluent_kafka import Consumer
import smtplib
from email.mime.text import MIMEText
import json
import os

# Configurazione Kafka per il Consumer
kafka_config_consumer = {
    'bootstrap.servers': 'kafka:9092',
    'group.id': 'notifier-system-group',
    'auto.offset.reset': 'earliest'
}

consumer = Consumer(kafka_config_consumer)

# Configurazione del server SMTP (email) tramite variabili d'ambiente
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = os.getenv("SMTP_USER")  # Email prelevata dalle variabili d'ambiente
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")  # Password prelevata dalle variabili d'ambiente

def send_email(to_email, subject, body):
    """
    Invia un'email utilizzando il server SMTP configurato.
    """
    try:
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = SMTP_USER
        msg['To'] = to_email

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, to_email, msg.as_string())
            print(f"[INFO] Email inviata con successo a {to_email}")
    except Exception as e:
        print(f"[ERROR] Errore nell'invio dell'email: {e}")

def process_notifier_message(message):
    """
    Elabora i messaggi ricevuti dal topic 'to-notifier' e invia notifiche.
    """
    try:
        data = json.loads(message.value().decode('utf-8'))
        print(f"[INFO] Messaggio ricevuto: {data}")

        email = data.get("email")
        ticker = data.get("ticker")
        condition = data.get("condition")

        if email and ticker and condition:
            subject = f"Alert: {ticker} ha superato la soglia!"
            body = f"Il ticker {ticker} ha soddisfatto la condizione: {condition}.\nVerifica subito!"
            send_email(email, subject, body)
        else:
            print("[WARNING] Dati mancanti nel messaggio ricevuto. Email non inviata.")

    except Exception as e:
        print(f"[ERROR] Errore nell'elaborazione del messaggio: {e}")

def consume_notifications():
    """
    Consuma messaggi dal topic 'to-notifier' e invia notifiche.
    """
    consumer.subscribe(['to-notifier'])

    print("[INFO] In ascolto sul topic 'to-notifier'...")
    try:
        while True:
            msg = consumer.poll(1.0)  # Attende messaggi per 1 secondo
            if msg is None:
                continue
            if msg.error():
                print(f"[ERROR] Errore nel messaggio Kafka: {msg.error()}")
                continue

            # Elabora il messaggio ricevuto
            process_notifier_message(msg)

    except KeyboardInterrupt:
        print("[INFO] Chiusura del consumer Kafka...")
    except Exception as e:
        print(f"[ERROR] Errore durante l'esecuzione del consumer: {e}")
    finally:
        consumer.close()

if __name__ == "__main__":
    consume_notifications()