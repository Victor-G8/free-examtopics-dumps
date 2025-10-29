FROM python:3.13-slim

WORKDIR /app

# Installer Chromium et dépendances nécessaires
RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    fonts-liberation \
    libnss3 \
    libxss1 \
    libasound2 \
    libatk-bridge2.0-0 \
    libgtk-3-0 \
    libx11-xcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libpangocairo-1.0-0 \
 && rm -rf /var/lib/apt/lists/*

# Installer les dépendances Python
RUN pip install --no-cache-dir selenium pillow tqdm webdriver-manager

# Copier les scripts Python (pas le fichier urls.txt)
COPY scraper-and-pdf-generator.py complete-list.py /app/

# Variables d’environnement
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver

CMD ["python", "complete-list.py", "estimate"]
