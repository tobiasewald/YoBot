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

# Load system prompt with sarcasm
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
            if not logs:
                logging.warning("No vulnerabilities found in the Trivy logs.")
            return logs
    except json.JSONDecodeError as e:
        logging.error(f"Error decoding JSON from {log_path}: {e}")
        raise
    except Exception as e:
        logging.error(f"Error loading logs: {e}")
        raise

# Combine logs with the prompt
def build_prompt_with_logs(prompt_content, logs):
    try:
        logs_as_text = "\n\n".join([f"Vulnerability {i+1}: {log['Title']} - CVSS Score: {log['CVSS']['bitnami']['V3Score']}" for i, log in enumerate(logs)])
        full_prompt = prompt_content + "\n\nAnalyze the following logs with a touch of humor:\n" + logs_as_text
        return full_prompt
    except Exception as e:
        logging.error(f"Error building prompt: {e}")
        raise

# Send prompt to Ollama and return response using aiohttp
async def send_prompt_to_ollama(prompt, model="llama3.2", temperature=1.0):
    url = "http://ollama-service:11434/api/generate"
    payload = {
        "model": model,
        "prompt": prompt,
        "temperature": temperature,  # Set temperature for humor
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

# Extract information and add humor
def extract_and_humor_logs(logs):
    humor_response = []
    if isinstance(logs, list) and logs:  # Ensure that logs is a non-empty list
        for log in logs:
            title = log.get("Title", "No Title")
            severity = log.get("Severity", "Unknown Severity")
            cwe_ids = log.get("CweIDs", [])
            cvss_score = log.get("CVSS", {}).get("bitnami", {}).get("V3Score", "N/A")
            fixed_version = log.get("References", [])[0] if log.get("References") else "No fix available"

            # Add humor and security awareness
            humor_response.append(f"💥 **Security Alert:** {title} 💥\n"
                                  f"Severity: {severity} | CVSS Score: {cvss_score}\n"
                                  f"CWE IDs: {', '.join(cwe_ids)}\n"
                                  f"Fixed Version: {fixed_version}\n"
                                  f"🎉 **Recommended Action:** Please patch it before your code turns into a hacker's playground! 😎\n")
    else:
        logging.error(f"Logs are not in the expected list format or are empty: {logs}")
        humor_response.append("Error: Logs are in an unexpected format or empty.")
    return humor_response

# Main process
async def main():
    try:
        # Pull the required model
        await pull_model("llama3.2")

        # Load logs and prompts
        logs = load_trivy_logs()
        humor_prompt_txt = load_model_prompt(MODEL_HUMOR_PATH)

        # Build prompts
        humor_prompt = build_prompt_with_logs(humor_prompt_txt, logs)

        # Send prompts to model with a higher temperature for humor
        humor_response = await send_prompt_to_ollama(humor_prompt, temperature=1.0)

        # Generate humorous responses
        humorous_logs = extract_and_humor_logs(logs)

        # Combine model and humor logs
        full_message = "\n\n".join(humorous_logs) + "\n" + humor_response

        # Clean the final message
        safe_message = clean_discord_message(full_message)

        # Send to Discord
        await send_discord_message_async(safe_message)

    except Exception as e:
        logging.error(f"Error in main process: {e}")

# Entry point
if __name__ == "__main__":
    asyncio.run(main())
