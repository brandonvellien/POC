# Dockerfile FINAL (v3) - Approche simplifiée et robuste

# Étape 1 : Base NVIDIA (inchangée)
FROM nvidia/cuda:12.1.1-cudnn8-runtime-ubuntu22.04

# Étape 2 : Dépendances système + Python + Node.js (regroupés)
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    gnupg \
    wget \
    unzip \
    jq \
    ca-certificates \
    python3.11 \
    python3.11-dev \
    python3-pip \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Étape 3 : Configurer Python 3.11 par défaut (inchangée)
RUN ln -sf /usr/bin/python3.11 /usr/bin/python && \
    ln -sf /usr/bin/python3.11 /usr/bin/python3 && \
    curl https://bootstrap.pypa.io/get-pip.py | python

# === CORRECTION v3 : Installation de Chrome et du dernier ChromeDriver stable ===
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/google-chrome-keyring.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome-keyring.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && DRIVER_URL=$(wget -qO- https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json | jq -r '.channels.Stable.downloads.chromedriver[] | select(.platform=="linux64") | .url') \
    && wget -qP /tmp/ "$DRIVER_URL" \
    && unzip /tmp/chromedriver-linux64.zip -d /usr/local/bin/ \
    && rm -f /tmp/chromedriver-linux64.zip \
    && rm -rf /var/lib/apt/lists/*
# === FIN DE LA CORRECTION v3 ===

# Étape 4 : Définir le répertoire de travail
WORKDIR /app

# Étape 5 : Installer les dépendances Node.js
COPY backend/package.json backend/package-lock.json ./backend/
RUN npm install --prefix ./backend --omit=dev

# Étape 6 : Installer les dépendances Python
COPY backend/requirements.txt ./backend/
RUN pip install --no-cache-dir -r ./backend/requirements.txt

# Étape 7 : Copier le reste de l'application
COPY backend/ ./backend/

# Exposer le port
EXPOSE 8080

# Commande de démarrage
CMD ["node", "./backend/index.js"]