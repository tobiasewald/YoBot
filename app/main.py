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
MODEL_HUMOR_PATH = os.getenv('MODEL_HUMOR_PATH')

if not DISCORD_WEBHOOK_URL:
    raise ValueError("DISCORD_WEBHOOK_URL is missing in the .env file.")
if not MODEL_HUMOR_PATH:
    raise ValueError("MODEL_HUMOR_PATH is missing in the .env file.")

# Pull model from Ollama using aiohttp
async def pull_model(model_name):
    url = "http://ollama-service:11434/api/pull"
    payload = {"model": model_name}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                response.raise_for_status()
                logging.info(f"Model '{model_name}' pulled successfully.")
    except Exception as e:
        logging.error(f"Error pulling model {model_name}: {e}")
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

# Load Trivy logs from file
def load_trivy_logs(log_path="trivy_output.json"):
    try:
        with open(log_path, "r") as file:
            logs = json.load(file)
            logging.debug(f"Trivy logs loaded from {log_path}.")
            logging.debug(f"Loaded logs: {logs}")
            return logs
    except Exception as e:
        logging.error(f"Error loading logs: {e}")
        raise

# Combine logs with the prompt
def build_prompt_with_logs(prompt_content, logs):
    try:
        logs_as_text = json.dumps(logs, indent=2)
        full_prompt = prompt_content + "\n\nAnalyze the following logs with a touch of humor:\n" + logs_as_text
        return full_prompt
    except Exception as e:
        logging.error(f"Error building prompt: {e}")
        raise

# Send prompt to Ollama and return response using aiohttp
async def send_prompt_to_ollama(prompt, model="llama3.2"):
    url = "http://ollama-service:11434/api/generate"
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                response.raise_for_status()
                logging.info("Prompt sent to Ollama successfully.")
                return (await response.json()).get("response")
    except Exception as e:
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
        return ": Message could not be processed."

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

# Generate funny and helpful explanations from Trivy logs
def extract_and_humor_logs(logs):
    humor_response = []
    if isinstance(logs, list):
        for log in logs:
            title = log.get("Title", "Unnamed Vulnerability")
            severity = log.get("Severity", "Unknown")
            cve_id = log.get("VulnerabilityID", "N/A")
            description = log.get("Description", "No description available.")
            cvss_score = log.get("CVSS", {}).get("nvd", {}).get("V3Score", "N/A")
            cvss_vector = log.get("CVSS", {}).get("nvd", {}).get("Vectors", "N/A")

            humor_response.append(
                f"🔍 **Vulnerability:** {title}\n"
                f"🧬 **CVE ID:** {cve_id}\n"
                f"📜 **Description:** {description}\n"
                f"💣 **Severity:** {severity} | CVSS: {cvss_score} ({cvss_vector})\n"
                f"🤣 **YoBot says:** This one's like giving admin rights to your cat. Fluffy doesn't need root access.\n"
                f"✅ **Fix it:** Patch it now or face the wrath of the bugs!\n"
                f"{'-'*50}"
            )
    else:
        logging.error(f"Logs are not in the expected list format: {logs}")
        humor_response.append("⚠️ Error: Logs are in an unexpected format.")
    return humor_response

# Main process
async def main():
    try:
        await pull_model("llama3.2")

        logs = load_trivy_logs()
        humor_prompt_txt = load_model_prompt(MODEL_HUMOR_PATH)

        humor_prompt = build_prompt_with_logs(humor_prompt_txt, logs)

        model_response = await send_prompt_to_ollama(humor_prompt)

        humorous_logs = extract_and_humor_logs(logs)

        full_message = "\n\n".join(humorous_logs) + "\n🧠 **YoBot’s AI Wisdom:**\n" + model_response

        safe_message = clean_discord_message(full_message)

        await send_discord_message_async(safe_message)

    except Exception as e:
        logging.error(f"Error in main process: {e}")

# Entry point
if __name__ == "__main__":
    asyncio.run(main())
