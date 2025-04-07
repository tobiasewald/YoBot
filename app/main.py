import json
import logging
import os
import asyncio
import aiohttp
import ollama
from dotenv import load_dotenv

# Umgebungsvariablen laden
load_dotenv()

logging.basicConfig(level=logging.DEBUG)

DISCORD_WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_URL')
if not DISCORD_WEBHOOK_URL:
    logging.error("Discord Webhook URL fehlt.")
    raise ValueError("DISCORD_WEBHOOK_URL nicht gesetzt.")

MODEL_ANALYSIS_PATH = os.getenv('MODEL_ANALYSIS_PATH')
MODEL_HUMOR_PATH = os.getenv('MODEL_HUMOR_PATH')

if not MODEL_ANALYSIS_PATH or not MODEL_HUMOR_PATH:
    logging.error("Pfad zu Analyse- oder Humor-Modell fehlt.")
    raise ValueError("MODEL_ANALYSIS_PATH und MODEL_HUMOR_PATH müssen gesetzt sein.")

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

# Modell-Content laden
def load_model_prompt(model_path):
    try:
        with open(model_path, "r") as file:
            content = file.read()
            logging.debug(f"Modell-File {model_path} erfolgreich geladen.")
            return content
    except Exception as e:
        logging.error(f"Fehler beim Laden des Modells {model_path}: {e}")
        raise

# Antwort generieren mit geladenem Modellprompt
def generate_response_with_prompt(prompt_content, question):
    try:
        response = ollama.chat(
            model="llama3",
            messages=[
                {"role": "system", "content": prompt_content},
                {"role": "user", "content": question}
            ],
            options={"temperature": 0.3}
        )
        return response['message']['content']
    except Exception as e:
        logging.error(f"Fehler bei ollama.chat: {e}")
        raise

# Humorvolle Antwort generieren
def generate_humorous_response(logs):
    try:
        question = "Wie sicher ist mein Docker-Image?"

        analysis_prompt = load_model_prompt(MODEL_ANALYSIS_PATH)
        humor_prompt = load_model_prompt(MODEL_HUMOR_PATH)

        analysis_response = generate_response_with_prompt(analysis_prompt, question)
        humor_response = generate_response_with_prompt(humor_prompt, question)

        logging.debug(f"Analyse: {analysis_response}")
        logging.debug(f"Humor: {humor_response}")

        return humor_response
    except Exception as e:
        logging.error(f"Fehler bei der humorvollen Antwortgenerierung: {e}")
        raise

# Discord senden
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

# Main
async def main():
    try:
        trivy_logs = load_trivy_logs()
        humorous_response = generate_humorous_response(trivy_logs)
        await send_discord_message_async(humorous_response)
    except Exception as e:
        logging.error(f"Fehler im Hauptprozess: {e}")

if __name__ == "__main__":
    asyncio.run(main())
