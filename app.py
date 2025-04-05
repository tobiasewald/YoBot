from flask import Flask, jsonify
import random
import requests

app = Flask(__name__)

def get_ollama_suggestions(log_data):
    url = "http://localhost:8080/analyze-log"
    response = requests.post(url, json={"log": log_data})
    if response.status_code == 200:
        return response.json()["suggestions"]
    else:
        return "Keine Vorschläge verfügbar"

TELEGRAM_BOT_TOKEN = "dein-bot-token"
TELEGRAM_CHAT_ID = "deine-chat-id"

def send_telegram_message(message):
    telegram_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    requests.post(telegram_url, data=payload)

@app.route('/')
def hello():
    return "Hello, world!"

@app.route('/error')
def error():
    errors = ["Datenbankverbindung fehlgeschlagen", "Speicherleck entdeckt", "Unbefugter Zugriff erkannt"]
    error_message = random.choice(errors)

    # KI schlägt Fixes vor
    suggestions = get_ollama_suggestions(error_message)

    # Telegram-Nachricht senden
    send_telegram_message(f"Fehler aufgetreten: {error_message}")

    return jsonify({"error": error_message, "fix_suggestions": suggestions}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
