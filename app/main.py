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

# Combine logs with humor prompt
def build_prompt_with_logs(logs):
    try:
        with open(MODEL_HUMOR_PATH, "r") as file:
            humor_base = file.read().strip()

        if not isinstance(logs, list):
            logging.error("Error: Logs are not in the expected format.")
            return ""

        logs_as_text = "\n\n".join([
            f"💥 Vulnerability {i+1}: {log.get('Title', 'No Title')}\n"
            f"Severity: {log.get('Severity', 'N/A')} | CVSS Score: {log.get('CVSS', {}).get('bitnami', {}).get('V3Score', 'N/A')}\n"
            f"CWE IDs: {', '.join(log.get('CweIDs', [])) if log.get('CweIDs') else 'None'}\n"
            f"Fixed Version: {log.get('References', [])[0] if log.get('References') else 'N/A'}"
            for i, log in enumerate(logs)
        ])

        return (
            f"{humor_base}\n\n"
            f"Analyze the following security vulnerabilities and generate a humorous, yet informative summary for each:\n\n"
            f"{logs_as_text}\n\n"
            f"⚠️ Avoid repeating jokes and include a light recommendation."
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
                return (await response.json()).get("response")
    except Exception as e:
        logging.error(f"Ollama generate error: {e}")
        return "Error generating response from Ollama."

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

# Format response
def extract_and_generate_humor_from_model(logs, model_response):
    humor_response = []
    if isinstance(logs, list):
        for log in logs:
            title = log.get("Title", "No Title")
            severity = log.get("Severity", "Unknown")
            cwe_ids = log.get("CweIDs", [])
            cvss_score = log.get("CVSS", {}).get("bitnami", {}).get("V3Score", "N/A")
            fixed_version = log.get("References", [])[0] if log.get("References") else "No fix available"

            humor_response.append(f"💥 **Security Alert:** {title} 💥\n"
                                  f"Severity: {severity} | CVSS Score: {cvss_score}\n"
                                  f"CWE IDs: {', '.join(cwe_ids) if cwe_ids else 'None'}\n"
                                  f"Fixed Version: {fixed_version}\n"
                                  f"🎉 **Recommended Action:** {model_response}\n")
    else:
        logging.error("Logs are not in the expected format.")
        humor_response.append("Error: Logs are in an unexpected format.")

    return humor_response

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

        response = await send_prompt_to_ollama(prompt, temperature=1.0)
        humorous_logs = extract_and_generate_humor_from_model(logs, response)
        safe_message = clean_discord_message("\n\n".join(humorous_logs))
        await send_discord_message_async(safe_message)

    except Exception as e:
        logging.error(f"Error in main process: {e}")

if __name__ == "__main__":
    asyncio.run(main())
