# Dockerfile pour le service backend - VERSION FINALE ANTI-CACHE

# Étape 1: Image de base Node.js
FROM node:18

# Étape 2: Installation de Python et des dépendances nécessaires
RUN apt-get update && apt-get install -y python3 python3-pip python3.11-venv
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip3 install --upgrade pip
RUN pip3 install --upgrade torch torchvision diffusers transformers accelerate safetensors boto3

# Étape 3: Définir le dossier de travail
WORKDIR /usr/src/app

# Étape 4: Copier les fichiers de dépendances
COPY package*.json ./

# Étape 5: Utiliser 'npm ci' pour une installation propre et fiable basée sur le lockfile
RUN npm ci --omit=dev

# Étape 6: Copier le reste du code
COPY . .

# Étape 7: Exposer le port
EXPOSE 3000

# Étape 8: Commande de démarrage
CMD [ "node", "index.js" ]