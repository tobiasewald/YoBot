import requests
import logging
import json
import asyncio
import aiohttp
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Variables from the .env file
DISCORD_WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_URL')
MODEL_ANALYSIS_PATH = os.getenv('MODEL_ANALYSIS_PATH')
MODEL_HUMOR_PATH = os.getenv('MODEL_HUMOR_PATH')

if not DISCORD_WEBHOOK_URL:
    raise ValueError("DISCORD_WEBHOOK_URL is missing in the .env file.")
if not MODEL_ANALYSIS_PATH or not MODEL_HUMOR_PATH:
    raise ValueError("MODEL_ANALYSIS_PATH or MODEL_HUMOR_PATH is missing in the .env file.")

# Pull model from Ollama
def pull_model(model_name):
    url = "http://ollama-service:11434/api/pull"
    payload = {"model": model_name}

    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        logging.info(f"Model '{model_name}' pulled successfully.")
    except requests.exceptions.RequestException as e:
        logging.error(f"Error pulling model {model_name}: {e}")
        raise

# Load Trivy logs from file
def load_trivy_logs(log_path="trivy_output.json"):
    try:
        with open(log_path, "r") as file:
            logs = json.load(file)
            logging.debug(f"Trivy logs loaded from {log_path}.")
            return logs
    except Exception as e:
        logging.error(f"Error loading logs: {e}")
        raise

# Load system prompt
def load_model_prompt(prompt_path):
    try:
        with open(prompt_path, "r") as file:
            content = file.read()
            logging.debug(f"Prompt file {prompt_path} loaded.")
            return content
    except Exception as e:
        logging.error(f"Error loading prompt: {e}")
        raise

# Combine logs with the prompt
def build_prompt_with_logs(prompt_content, logs):
    try:
        logs_as_text = json.dumps(logs, indent=2)
        full_prompt = prompt_content + "\n\nAnalyze the following logs:\n" + logs_as_text
        return full_prompt
    except Exception as e:
        logging.error(f"Error building prompt: {e}")
        raise

# Send prompt to Ollama and return response
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
        logging.info("Prompt sent to Ollama successfully.")
        return response.json().get("response")
    except requests.exceptions.RequestException as e:
        logging.error(f"Ollama generate error: {e}")
        raise

# Clean and trim message for Discord
def clean_discord_message(text, max_length=1900):
    try:
        cleaned = text.encode("utf-8", "ignore").decode("utf-8")
        cleaned = cleaned.replace('\u0000', '')
        if len(cleaned) > max_length:
            cleaned = cleaned[:max_length] + "\n... (truncated)"
        return cleaned
    except Exception as e:
        logging.error(f"Error cleaning message: {e}")
        return "⚠️ Message could not be processed."

# Send message to Discord
async def send_discord_message_async(message):
    try:
        payload = {"content": message}
        headers = {"Content-Type": "application/json"}

        logging.debug(f"Discord Payload: {json.dumps(payload)}")

        async with aiohttp.ClientSession() as session:
            async with session.post(DISCORD_WEBHOOK_URL, json=payload, headers=headers) as response:
                if response.status == 204:
                    logging.debug("Message sent to Discord.")
                else:
                    logging.error(f"Discord responded with status: {response.status}")
    except Exception as e:
        logging.error(f"Error sending to Discord: {e}")

# Main process
async def main():
    try:
        # Pull the required model
        pull_model("llama3.2")

        # Load logs and prompts
        logs = load_trivy_logs()
        analysis_prompt_txt = load_model_prompt(MODEL_ANALYSIS_PATH)
        humor_prompt_txt = load_model_prompt(MODEL_HUMOR_PATH)

        # Build prompts
        analysis_prompt = build_prompt_with_logs(analysis_prompt_txt, logs)
        humor_prompt = build_prompt_with_logs(humor_prompt_txt, logs)

        # Send prompts to model
        analysis_response = send_prompt_to_ollama(analysis_prompt)
        humor_response = send_prompt_to_ollama(humor_prompt)

        # Combine and clean the final message
        combined_message = f"🔍 **Security Analysis**:\n{analysis_response}\n\n😂 **Humorous Summary**:\n{humor_response}"
        safe_message = clean_discord_message(combined_message)

        # Send to Discord
        await send_discord_message_async(safe_message)

    except Exception as e:
        logging.error(f"Error in main process: {e}")

# Entry point
if __name__ == "__main__":
    asyncio.run(main())
