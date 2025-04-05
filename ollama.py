import requests

def get_ollama_suggestions(log_data):
    url = "http://localhost:8080/analyze-log"
    response = requests.post(url, json={"log": log_data})
    if response.status_code == 200:
        return response.json()["suggestions"]
    else:
        return "Keine Vorschläge verfügbar"
