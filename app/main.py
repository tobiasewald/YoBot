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

# Load Trivy logs from file
def load_trivy_logs(log_path="trivy_output.json"):
    try:
        with open(log_path, "r") as file:
            raw_data = json.load(file)
            logging.debug(f"Raw Trivy log content: {json.dumps(raw_data, indent=2)}")

            vulnerabilities = []
            if isinstance(raw_data, dict) and "Results" in raw_data:
                for result in raw_data["Results"]:
                    vulns = result.get("Vulnerabilities", [])
                    if isinstance(vulns, list):
                        vulnerabilities.extend(vulns)
            elif isinstance(raw_data, dict) and "vulnerabilities" in raw_data:
                vulnerabilities = raw_data["vulnerabilities"]

            if not isinstance(vulnerabilities, list):
                logging.error("Log format error: Logs should be a list of dictionaries.")
                return []

            logging.info(f"Extracted {len(vulnerabilities)} vulnerability entries.")
            return vulnerabilities
    except Exception as e:
        logging.error(f"Error loading logs: {e}")
        return []

# Build funny + sarcastic prompt with logs
def build_prompt_with_logs(logs):
    try:
        with open(MODEL_HUMOR_PATH, "r") as file:
            humor_base = file.read().strip()

        logs_as_text = "\n\n".join([
            f"🔥 Vulnerability {i+1}: {log.get('Title', 'No Title')}\n"
            f"Severity: {log.get('Severity', 'N/A')} | CVSS: {log.get('CVSS', {}).get('bitnami', {}).get('V3Score', 'N/A')}\n"
            f"CWE: {', '.join(log.get('CweIDs', [])) if log.get('CweIDs') else 'None'}\n"
            f"Fix it (maybe?): {log.get('References', [])[0] if log.get('References') else 'No clue, good luck'}"
            for i, log in enumerate(logs)
        ])

        return (
            f"{humor_base}\n\n"
            f"You are YoBot — a sarcastic AI DevSecOps assistant who turns boring security reports into hilarious, meme-worthy Slack/Discord messages.\n\n"
            f"Your style is inspired by:\n"
            f"- Gordon Ramsay yelling at bugs\n"
            f"- A stand-up comedian doing infosec\n"
            f"- A DevOps intern who’s had enough\n\n"
            f"Now, here's a list of vulnerabilities. For each one, roast it, mock its severity like a drama queen, and end with a funny (but useful) recommendation.\n\n"
            f"{logs_as_text}\n\n"
            f"🎭 Keep it short, sharp, sassy, and never boring. Go full Sheldon Cooper if needed."
        )
    except Exception as e:
        logging.error(f"Error building prompt with humor path: {e}")
        return ""

# Send prompt to Ollama
async def send_prompt_to_ollama(prompt, model="llama3.2", temperature=1.0):
    url = "http://ollama-service:11434/api/generate"
    payload = {
        "model": model,
        "prompt": prompt,
        "temperature": temperature,
        "stream": False
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                response.raise_for_status()
                logging.info("Prompt sent to Ollama successfully.")
                result = await response.json()
                return result.get("response", "No funny response generated.")
    except Exception as e:
        logging.error(f"Ollama generate error: {e}")
        return "Oops, I tried to be funny, but I crashed harder than your CI pipeline."

# Clean output for Discord
def clean_discord_message(text, max_length=1900):
    try:
        cleaned = text.encode("utf-8", "ignore").decode("utf-8").replace('\u0000', '')
        if len(cleaned) > max_length:
            cleaned = cleaned[:max_length] + "\n... (truncated)"
        return cleaned
    except Exception as e:
        logging.error(f"Error cleaning message: {e}")
        return ": Message could not be processed."

# Send to Discord
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

# Main entry
async def main():
    try:
        await pull_model("llama3.2")
        logs = load_trivy_logs()
        if not logs:
            logging.error("No valid logs to process.")
            return

        prompt = build_prompt_with_logs(logs)
        if not prompt:
            logging.error("Failed to build prompt.")
            return

        response = await send_prompt_to_ollama(prompt, temperature=1.1)
        final_message = clean_discord_message(response)
        await send_discord_message_async(final_message)

    except Exception as e:
        logging.error(f"Error in main process: {e}")

if __name__ == "__main__":
    asyncio.run(main())
