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

# Load Trivy logs from file and ensure correct structure
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

            # Final structure check
            if not isinstance(vulnerabilities, list):
                logging.error("Log format error: Logs should be a list of dictionaries.")
                return []

            logging.info(f"Extracted {len(vulnerabilities)} vulnerability entries.")
            return vulnerabilities
    except ValueError as e:
        logging.error(f"Log format error: {e}")
        return []
    except Exception as e:
        logging.error(f"Error loading logs: {e}")
        return []


# Combine logs with the prompt
def build_prompt_with_logs(prompt_content, logs):
    try:
        # Ensure that logs are in the correct format (list of dictionaries)
        if not isinstance(logs, list):
            logging.error("Error: Logs are not in the expected format.")
            return ""
        
        logs_as_text = "\n\n".join([f"Vulnerability {i+1}: {log.get('Title', 'No Title')} - CVSS Score: {log.get('CVSS', {}).get('bitnami', {}).get('V3Score', 'N/A')}" for i, log in enumerate(logs)])
        full_prompt = prompt_content + "\n\nAnalyze the following logs with a touch of humor:\n" + logs_as_text
        return full_prompt
    except Exception as e:
        logging.error(f"Error building prompt: {e}")
        return ""

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
        return "Error generating response from Ollama."

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

# Extract information and allow the model to generate humor automatically
def extract_and_generate_humor_from_model(logs, model_response):
    humor_response = []
    if isinstance(logs, list):  # Ensure that logs is a list
        for log in logs:
            title = log.get("Title", "No Title")
            severity = log.get("Severity", "Unknown Severity")
            cwe_ids = log.get("CweIDs", [])
            cvss_score = log.get("CVSS", {}).get("bitnami", {}).get("V3Score", "N/A")
            fixed_version = log.get("References", [])[0] if log.get("References") else "No fix available"
            
            # Generate humor based on the model response
            humor_response.append(f"💥 **Security Alert:** {title} 💥\n"
                                  f"Severity: {severity} | CVSS Score: {cvss_score}\n"
                                  f"CWE IDs: {', '.join(cwe_ids) if cwe_ids else 'None'}\n"
                                  f"Fixed Version: {fixed_version}\n"
                                  f"🎉 **Recommended Action:** {model_response}\n")
    else:
        logging.error(f"Logs are not in the expected list format: {logs}")
        humor_response.append("Error: Logs are in an unexpected format.")
    
    return humor_response

# Main process
async def main():
    try:
        # Pull the required model
        await pull_model("llama3.2")

        # Load logs and prompts
        logs = load_trivy_logs()
        if not logs:  # Exit early if logs are empty or have an error
            logging.error("No valid logs to process.")
            return

        humor_prompt_txt = load_model_prompt(MODEL_HUMOR_PATH)

        # Build prompts
        humor_prompt = build_prompt_with_logs(humor_prompt_txt, logs)

        if not humor_prompt:  # Exit early if there's an issue with the prompt
            logging.error("Failed to build a valid prompt.")
            return

        # Send prompts to model with a higher temperature for humor
        humor_response = await send_prompt_to_ollama(humor_prompt, temperature=1.0)

        # Generate humorous responses
        humorous_logs = extract_and_generate_humor_from_model(logs, humor_response)

        # Combine model and humor logs
        full_message = "\n\n".join(humorous_logs)

        # Clean the final message
        safe_message = clean_discord_message(full_message)

        # Send to Discord
        await send_discord_message_async(safe_message)

    except Exception as e:
        logging.error(f"Error in main process: {e}")

# Entry point
if __name__ == "__main__":
    asyncio.run(main())
