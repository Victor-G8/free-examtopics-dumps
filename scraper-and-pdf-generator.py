import os
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from PIL import Image

# ==============================
# 🔧 CONFIGURATION
# ==============================
URLS_FILE = "urls.txt"
PDF_NAME = "dump.pdf"

A4_WIDTH, A4_HEIGHT = 1240, 1754  # A4 portrait à 150 dpi
MARGIN = 40  # marge autour du contenu
MAX_PAGE_HEIGHT = 5000  # sécurité (évite de capturer des pages trop énormes)
# ==============================

Image.init()

options = Options()
options.binary_location = "/usr/bin/chromium"
options.add_argument("--headless=new")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-gpu")
options.add_argument("--window-size=1920,1080")

service = Service("/usr/bin/chromedriver")
driver = webdriver.Chrome(service=service, options=options)

# Lecture des URLs
if not os.path.exists(URLS_FILE):
    raise FileNotFoundError(f"Le fichier {URLS_FILE} est introuvable.")

with open(URLS_FILE, "r", encoding="utf-8") as f:
    urls = [line.strip() for line in f if line.strip()]

SELECTORS = [
    "div.discussion-list-header",
    "div.discussion-header-container",
    "div.discussion-page-comments-section",
]

all_pages = []

for url in urls:
    print(f"→ Traitement de {url}")

    match = re.search(r"/(\d+)-.*?-(\d+)-discussion", url)
    if not match:
        print("❌ Impossible d’extraire les IDs dans l’URL.")
        continue

    question_id, discussion_id = match.groups()

    try:
        driver.get(url)
        scroll_height = driver.execute_script("return document.body.scrollHeight")
        driver.set_window_size(1920, scroll_height)

        # Clic sur le bouton "Show Suggested Answer"
        try:
            button = driver.find_element(By.CSS_SELECTOR, "a.btn.btn-primary.reveal-solution")
            driver.execute_script("arguments[0].click();", button)
        except Exception:
            pass

        # Capturer les blocs
        images = []
        for selector in SELECTORS:
            try:
                el = driver.find_element(By.CSS_SELECTOR, selector)
                temp_path = f"_tmp_{discussion_id}_{selector.split('.')[-1]}.png"
                el.screenshot(temp_path)
                images.append(temp_path)
            except Exception as e:
                print(f"⚠️ Bloc {selector} introuvable :", e)

        if not images:
            print(f"⚠️ Aucun bloc capturé pour la question {discussion_id}.")
            continue

        # Fusion verticale
        opened = [Image.open(img) for img in images]
        total_height = sum(i.height for i in opened)
        max_width = max(i.width for i in opened)
        combined = Image.new("RGB", (max_width, total_height), (255, 255, 255))
        y = 0
        for i in opened:
            combined.paste(i, (0, y))
            y += i.height

        # Nettoyage
        for p in images:
            os.remove(p)

        # Découpage intelligent selon ratio A4
        aspect_ratio = A4_HEIGHT / A4_WIDTH
        current_top = 0
        while current_top < combined.height:
            # Détermine la hauteur qui correspond au ratio A4
            page_height = int(combined.width * aspect_ratio)
            bottom = min(current_top + page_height, combined.height)

            # Si le bloc restant est trop petit, on le garde tel quel
            if bottom - current_top < page_height * 0.4:
                bottom = combined.height

            page = combined.crop((0, current_top, combined.width, bottom))
            current_top = bottom

            # Redimensionnement pour A4 tout en remplissant la page
            ratio = min((A4_WIDTH - 2 * MARGIN) / page.width, (A4_HEIGHT - 2 * MARGIN) / page.height)
            new_size = (int(page.width * ratio), int(page.height * ratio))
            page_resized = page.resize(new_size, Image.LANCZOS)

            # Création page A4 blanche
            a4_page = Image.new("RGB", (A4_WIDTH, A4_HEIGHT), (255, 255, 255))
            x_offset = (A4_WIDTH - page_resized.width) // 2
            y_offset = (A4_HEIGHT - page_resized.height) // 2
            a4_page.paste(page_resized, (x_offset, y_offset))

            all_pages.append(a4_page)

    except Exception as e:
        print(f"❌ Erreur sur {url} :", e)

driver.quit()

# Création du PDF final
if all_pages:
    first_page = all_pages[0]
    rest_pages = all_pages[1:]
    first_page.save(PDF_NAME, save_all=True, append_images=rest_pages)
    print(f"✔️ PDF global créé : {PDF_NAME}")
else:
    print("⚠️ Aucun PDF créé, aucune image disponible.")
