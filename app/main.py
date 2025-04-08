import requests
import logging
import json
import asyncio
import aiohttp
import os
from dotenv import load_dotenv

# Lade Umgebungsvariablen aus der .env-Datei
load_dotenv()

# Discord Webhook URL aus der Umgebungsvariablen laden
DISCORD_WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_URL')

# Logging konfigurieren
logging.basicConfig(level=logging.DEBUG)

# Modell von Ollama laden
def pull_model():
    url = "http://ollama-service:11434/api/pull"
    payload = { "model": "llama3.2" }

    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        logging.info("Modell erfolgreich gepullt.")
    except requests.exceptions.RequestException as e:
        logging.error(f"Modell-Pull fehlgeschlagen: {e}")
        raise

# Trivy-Logs laden
def load_trivy_logs(log_path="trivy_output.json"):
    try:
        with open(log_path, "r") as file:
            logs = json.load(file)
            logging.debug(f"Trivy-Logs von {log_path} erfolgreich geladen.")
            return logs
    except Exception as e:
        logging.error(f"Fehler beim Laden der Logs: {e}")
        raise

# Prompt vorbereiten
def prepare_analysis_prompt(logs):
    try:
        logs_as_text = json.dumps(logs, indent=2)
        prompt = (
            "Analysiere folgenden Trivy-Sicherheitsbericht und gib eine strukturierte Zusammenfassung:\n\n"
            "- Liste die Schwachstellen nach Kritikalität (HIGH, MEDIUM, LOW).\n"
            "- Gib Empfehlungen zur Behebung.\n"
            "- Nenne betroffene Pakete und Versionen.\n\n"
            f"{logs_as_text}"
        )
        logging.debug("Prompt erfolgreich vorbereitet.")
        return prompt
    except Exception as e:
        logging.error(f"Fehler beim Erstellen des Prompts: {e}")
        raise

# Prompt an Ollama senden
def send_prompt_to_ollama(prompt):
    url = "http://ollama-service:11434/api/generate"
    payload = {
        "model": "llama3.2",
        "prompt": prompt,
        "stream": False
    }

    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        logging.info("Prompt erfolgreich an Ollama gesendet.")
        return response.json().get("response")
    except requests.exceptions.RequestException as e:
        logging.error(f"Fehler beim Senden des Prompts: {e}")
        raise

# Discord-Nachricht senden
async def send_discord_message_async(message):
    try:
        payload = {"content": message}
        headers = {"Content-Type": "application/json"}

        async with aiohttp.ClientSession() as session:
            async with session.post(DISCORD_WEBHOOK_URL, json=payload, headers=headers) as response:
                if response.status == 204:
                    logging.debug("Nachricht erfolgreich an Discord gesendet.")
                else:
                    logging.error(f"Fehler beim Senden: {response.status}")
    except Exception as e:
        logging.error(f"Fehler beim Discord-Senden: {e}")

# Hauptablauf
async def main():
    pull_model()
    logs = load_trivy_logs("trivy_output.json")
    prompt = prepare_analysis_prompt(logs)
    ollama_response = send_prompt_to_ollama(prompt)
    await send_discord_message_async(ollama_response)

# Asynchron starten
if __name__ == "__main__":
    asyncio.run(main())
