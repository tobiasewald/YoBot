import requests
import logging
import json
import asyncio
import aiohttp
import os
from dotenv import load_dotenv

# Umgebungsvariablen laden
load_dotenv()

# Logging konfigurieren
logging.basicConfig(level=logging.DEBUG)

# Variablen aus der .env-Datei
DISCORD_WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_URL')
MODEL_ANALYSIS_PATH = os.getenv('MODEL_ANALYSIS_PATH')
MODEL_HUMOR_PATH = os.getenv('MODEL_HUMOR_PATH')

if not DISCORD_WEBHOOK_URL:
    raise ValueError("DISCORD_WEBHOOK_URL fehlt in der .env-Datei.")
if not MODEL_ANALYSIS_PATH or not MODEL_HUMOR_PATH:
    raise ValueError("MODEL_ANALYSIS_PATH oder MODEL_HUMOR_PATH fehlen in der .env-Datei.")

# Modell ziehen
def pull_model(model_name):
    url = "http://ollama-service:11434/api/pull"
    payload = { "model": model_name }

    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        logging.info(f"Modell '{model_name}' erfolgreich gepullt.")
    except requests.exceptions.RequestException as e:
        logging.error(f"Fehler beim Pullen des Modells {model_name}: {e}")
        raise

# Trivy-Logs laden
def load_trivy_logs(log_path="trivy_output.json"):
    try:
        with open(log_path, "r") as file:
            logs = json.load(file)
            logging.debug(f"Trivy-Logs von {log_path} geladen.")
            return logs
    except Exception as e:
        logging.error(f"Fehler beim Laden der Logs: {e}")
        raise

# System Prompt laden
def load_model_prompt(prompt_path):
    try:
        with open(prompt_path, "r") as file:
            content = file.read()
            logging.debug(f"Prompt-Datei {prompt_path} geladen.")
            return content
    except Exception as e:
        logging.error(f"Fehler beim Laden des Prompts: {e}")
        raise

# Prompt für Analyse
def build_prompt_with_logs(prompt_content, logs):
    try:
        logs_as_text = json.dumps(logs, indent=2)
        full_prompt = prompt_content + "\n\nAnalyse die folgenden Logs:\n" + logs_as_text
        return full_prompt
    except Exception as e:
        logging.error(f"Fehler beim Erstellen des Prompts: {e}")
        raise

# Prompt an Ollama senden
def send_prompt_to_ollama(prompt, model="llama3.2"):
    url = "http://ollama-service:11434/api/generate"
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False
    }

    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        logging.info("Prompt erfolgreich an Ollama gesendet.")
        return response.json().get("response")
    except requests.exceptions.RequestException as e:
        logging.error(f"Fehler bei ollama.generate: {e}")
        raise

# Discord-Nachricht senden
async def send_discord_message_async(message):
    try:
        payload = {"content": message}
        headers = {"Content-Type": "application/json"}

        async with aiohttp.ClientSession() as session:
            async with session.post(DISCORD_WEBHOOK_URL, json=payload, headers=headers) as response:
                if response.status == 204:
                    logging.debug("Nachricht an Discord gesendet.")
                else:
                    logging.error(f"Discord antwortet mit Status: {response.status}")
    except Exception as e:
        logging.error(f"Fehler beim Discord-Senden: {e}")

# Hauptfunktion
async def main():
    try:
        # Beide Modelle vorbereiten
        pull_model("llama3.2")

        logs = load_trivy_logs()
        analysis_prompt_txt = load_model_prompt(MODEL_ANALYSIS_PATH)
        humor_prompt_txt = load_model_prompt(MODEL_HUMOR_PATH)

        analysis_prompt = build_prompt_with_logs(analysis_prompt_txt, logs)
        humor_prompt = build_prompt_with_logs(humor_prompt_txt, logs)

        analysis_response = send_prompt_to_ollama(analysis_prompt)
        humor_response = send_prompt_to_ollama(humor_prompt)

        combined_message = f"🔍 **Sicherheitsanalyse**:\n{analysis_response}\n\n😂 **Humorvolle Einschätzung**:\n{humor_response}"
        await send_discord_message_async(combined_message)

    except Exception as e:
        logging.error(f"Fehler im Hauptprozess: {e}")

# Einstiegspunkt
if __name__ == "__main__":
    asyncio.run(main())
