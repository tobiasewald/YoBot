import requests

def pull_model():
    url = "http://ollama-service:11434/api/pull"
    payload = { "model": "llama3.2" }

    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        print("Model pulled successfully:")
        print(response.text)
    except requests.exceptions.RequestException as e:
        print("Request failed:")
        print(e)

if __name__ == "__main__":
    pull_model()
