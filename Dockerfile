# Verwende ein Basis-Image mit Python
FROM python:3.9-slim

# Setze das Arbeitsverzeichnis im Container
WORKDIR /app

# Kopiere die requirements.txt Datei ins Container
COPY requirements.txt /app/

# Installiere die Abhängigkeiten
RUN pip install --no-cache-dir -r requirements.txt

# Kopiere den Rest des Codes ins Container
COPY . /app/

# Starte die Flask-Anwendung
CMD ["python", "app.py"]
