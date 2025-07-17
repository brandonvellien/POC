# Dockerfile pour le service frontend - VERSION FINALE CORRIGÉE

# Étape 1: Image de base Python.
FROM python:3.12-slim

# Étape 2: Installation de git, nécessaire pour CLIP.
RUN apt-get update && apt-get install -y git

# Étape 3: Définition du dossier de travail.
WORKDIR /app

# Étape 4: Copie de la liste des dépendances.
COPY requirements.txt .

# Étape 5: Installation des dépendances.
# On utilise --break-system-packages ici car c'est un conteneur dédié à Python.
# C'est une alternative reconnue à venv pour simplifier les Dockerfiles d'application.
RUN pip install --no-cache-dir --break-system-packages -r requirements.txt && \
    pip install git+https://github.com/openai/CLIP.git

# Étape 6: Copie du reste du code.
COPY . .

# Étape 7: Exposition du port.
EXPOSE 8501

# Étape 8: Commande de démarrage.
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]