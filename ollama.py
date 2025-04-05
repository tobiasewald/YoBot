import requests

def get_ollama_suggestions(log_data):
    url = "http://ollama-service:8081/analyze-log"  # Der Kubernetes-Service-Name
    response = requests.post(url, json={"log": log_data})
    if response.status_code == 200:
        return response.json()["suggestions"]
    else:
        return "Keine Vorschläge verfügbar"
