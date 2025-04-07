import json
import logging
import os
import requests
import asyncio
from langchain.chains import RetrievalQA
from langchain.vectorstores import FAISS
from langchain.llms import Ollama
from langchain.embeddings import OpenAIEmbeddings
from dotenv import load_dotenv
import aiohttp

# Lade Umgebungsvariablen aus der .env-Datei
load_dotenv()

# Logging-Konfiguration
logging.basicConfig(level=logging.DEBUG)

# Discord Webhook URL aus der Umgebungsvariablen laden
DISCORD_WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_URL')
if not DISCORD_WEBHOOK_URL:
    logging.error("Discord Webhook URL wurde nicht in der Umgebungsvariablen gesetzt.")
    raise ValueError("Discord Webhook URL fehlt in der Umgebungsvariablen")

# Lade Modellpfade aus der .env-Datei
MODEL_ANALYSIS_PATH = os.getenv('MODEL_ANALYSIS_PATH')
MODEL_HUMOR_PATH = os.getenv('MODEL_HUMOR_PATH')

if not MODEL_ANALYSIS_PATH or not MODEL_HUMOR_PATH:
    logging.error("Modellpfade fehlen in der .env-Datei.")
    raise ValueError("Modellpfade fehlen in der Umgebungsvariablen")

# Funktionsweise von Ollama: Holt das Modell für die Analyse und Humor
def load_ollama_model(model_path):
    try:
        with open(model_path, "r") as file:
            model_content = file.read()
            logging.debug(f"Modell {model_path} erfolgreich geladen.")
            return model_content
    except Exception as e:
        logging.error(f"Fehler beim Laden des Modells {model_path}: {e}")
        raise

# Holt Trivy-Logs und gibt sie in einem geeigneten Format zurück
def load_trivy_logs(log_path="/app/trivy_output.json"):
    try:
        with open(log_path, "r") as file:
            logs = json.load(file)
            logging.debug(f"Trivy-Logs von {log_path} erfolgreich geladen.")
            return logs
    except Exception as e:
        logging.error(f"Fehler beim Laden der Trivy-Logs von {log_path}: {e}")
        raise

# RAG-System einrichten
def setup_rag(trivy_logs):
    logging.debug("RAG-System wird eingerichtet...")

    embeddings = OpenAIEmbeddings()

    faiss_index = FAISS.from_texts([json.dumps(trivy_logs)], embeddings)

    # Lade die Modelle
    try:
        model_analysis = load_ollama_model(MODEL_ANALYSIS_PATH)
        model_humor = load_ollama_model(MODEL_HUMOR_PATH)
    except Exception as e:
        logging.error(f"Fehler beim Laden der Modelle: {e}")
        raise

    # Ollama-Modelle für Analyse und Humor
    ollama_analysis_model = Ollama(model=model_analysis)
    ollama_humor_model = Ollama(model=model_humor)

    # RAG-Ketten einrichten
    chain_analysis = RetrievalQA.from_chain_type(llm=ollama_analysis_model, chain_type="stuff", retriever=faiss_index.as_retriever())
    chain_humor = RetrievalQA.from_chain_type(llm=ollama_humor_model, chain_type="stuff", retriever=faiss_index.as_retriever())

    logging.debug("RAG-System erfolgreich eingerichtet.")
    return chain_analysis, chain_humor

# Generiert eine humorvolle Antwort
def generate_humorous_response(chain_humor, chain_analysis, question):
    logging.debug(f"Frage an das RAG-System: {question}")

    try:
        analysis_response = chain_analysis.run(question)
        humor_response = chain_humor.run(question)
        logging.debug(f"Antworten: Analyse: {analysis_response}, Humor: {humor_response}")
        return humor_response
    except Exception as e:
        logging.error(f"Fehler bei der Generierung der humorvollen Antwort: {e}")
        raise

# Asynchrone Funktion zum Senden einer Nachricht an Discord über Webhook
async def send_discord_message_async(message):
    try:
        payload = {
            "content": message
        }
        headers = {
            "Content-Type": "application/json"
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(DISCORD_WEBHOOK_URL, json=payload, headers=headers) as response:
                if response.status == 204:
                    logging.debug("Nachricht erfolgreich an Discord gesendet.")
                else:
                    logging.error(f"Fehler beim Senden der Nachricht an Discord: {response.status}")
    except Exception as e:
        logging.error(f"Fehler beim Senden der Nachricht an Discord: {e}")

# Hauptprozess
async def main():
    try:
        trivy_logs = load_trivy_logs()
        chain_analysis, chain_humor = setup_rag(trivy_logs)

        question = "Wie sicher ist mein Docker-Image?"
        humorous_response = generate_humorous_response(chain_humor, chain_analysis, question)

        logging.debug(f"Humorvolle Antwort: {humorous_response}")
        await send_discord_message_async(humorous_response)
    except Exception as e:
        logging.error(f"Fehler im Hauptprozess: {e}")

if __name__ == "__main__":
    asyncio.run(main())
