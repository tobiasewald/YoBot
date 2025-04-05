from flask import Flask, request, jsonify
import requests
from transformers import GPT2LMHeadModel, GPT2Tokenizer

# Initialize Flask
app = Flask(__name__)

# Direkter Humor-Prompt als String im Code
prompt = """
You are a security analyst with deep knowledge of system logs and cybersecurity. Carefully inspect the syslog lines that follow.
Identify any suspicious, abnormal, or malicious behavior. Summarize potential threats.
Do not output anything related to recommendations. Just answer the analysis.
"""

# Ollama setup (for log analysis)
def get_ollama_suggestions(log_data):
    # Kombiniere den Log-Daten mit dem festgelegten Prompt
    request_payload = {
        "log": log_data,
        "prompt": prompt
    }
    
    # Ollama-API-Aufruf
    url = "http://ollama-service:11434/generate"  # Ollama Service URL
    response = requests.post(url, json=request_payload)
    
    if response.status_code == 200:
        return response.json().get("text", "No suggestions available")
    else:
        return "Oops! Something went wrong. I think the log's gone rogue!"


# Hugging Face setup (GPT-2 for humor)
model_name = "gpt2"
model = GPT2LMHeadModel.from_pretrained(model_name)
tokenizer = GPT2Tokenizer.from_pretrained(model_name)

def generate_humor(error_message):
    input_text = f"Error detected: {error_message}. How do we fix it humorously?"
    inputs = tokenizer.encode(input_text, return_tensors="pt")
    outputs = model.generate(inputs, max_length=100, num_return_sequences=1)
    humor = tokenizer.decode(outputs[0], skip_special_tokens=True)
    return humor

# Flask route for error analysis and humor generation
@app.route('/analyze-log', methods=['POST'])
def analyze_log():
    log_data = request.json.get('log', '')
    if not log_data:
        return jsonify({'error': 'No log data provided'}), 400
    
    # Get error suggestions from Ollama
    error_message = get_ollama_suggestions(log_data)
    
    # Generate humor based on the error message (Hugging Face GPT-2)
    humor_response = generate_humor(error_message)
    
    return jsonify({
        'error_message': error_message,
        'humor': humor_response
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)