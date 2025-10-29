#!/usr/bin/env python3
import sys
import re
import random
import string
import time
import os
from urllib.parse import urljoin, urlparse
from tqdm import tqdm

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait

URLS_FILE = "urls.txt"
LOG_FILE = "complete-list-output.txt"
RESTART_INTERVAL = 50  # Restart browser every 50 requests


# -------------------- Logging helper --------------------
def log(msg):
    """Print to console and append to log file."""
    print(msg)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(msg + "\n")


# -------------------- URL helpers --------------------
def load_urls():
    if not os.path.exists(URLS_FILE):
        return []
    with open(URLS_FILE, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def extract_id(url):
    match = re.search(r"/view/(\d+)-", url)
    return int(match.group(1)) if match else None


def extract_question_number(url):
    match = re.search(r"question-(\d+)", url)
    return int(match.group(1)) if match else None


def extract_base_url(url):
    match = re.match(r"^(https?://[^/]+/.*/view/)", url)
    return match.group(1) if match else None


# -------------------- Selenium helpers --------------------
def ensure_driver():
    """Start a minimal Chrome instance for Docker environment."""
    options = Options()
    options.binary_location = "/usr/bin/chromium"
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.page_load_strategy = "eager"

    prefs = {
        "profile.managed_default_content_settings.images": 2,
        "profile.managed_default_content_settings.stylesheets": 2,
        "profile.managed_default_content_settings.fonts": 2,
        "profile.managed_default_content_settings.javascript": 1
    }
    options.add_experimental_option("prefs", prefs)

    service = Service("/usr/bin/chromedriver")
    driver = webdriver.Chrome(service=service, options=options)
    return driver


def wait_for_ready(driver, timeout=10):
    """Wait for the page to be at least interactive."""
    try:
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script("return document.readyState") in ["interactive", "complete"]
        )
    except Exception:
        pass


# -------------------- Estimate range --------------------
def estimate_range():
    urls = load_urls()
    ids = [extract_id(u) for u in urls if extract_id(u)]
    if not ids:
        log("No IDs found in urls.txt")
        return
    min_id, max_id = min(ids), max(ids)
    log(f"Minimum ID: {min_id}")
    log(f"Maximum ID: {max_id}")
    log(f"Estimated range: {min_id}-{max_id}")
    log(f"Possible values: {max_id - min_id}")
    return min_id, max_id


# -------------------- Search missing --------------------
def search_missing(nb_questions, start_id, end_id, headless=True, cookies=None, slow_down=0.2):
    # Clear previous log
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write(f"Search started at {time.ctime()}\n")

    urls = load_urls()
    if not urls:
        log("urls.txt is empty or missing.")
        return

    base_url = extract_base_url(urls[0])
    base_match = re.search(r"(exam-[^/]+-topic-\d+-)", urls[0])

    if not base_url or not base_match:
        log("❌ Cannot identify base URL or topic pattern correctly.")
        sys.exit(1)

    topic_prefix = base_match.group(1)
    present_questions = sorted(set(extract_question_number(u) for u in urls if extract_question_number(u)))
    missing_questions = [i for i in range(1, nb_questions + 1) if i not in present_questions]

    log(f"Base URL: {base_url}")
    log(f"Present questions: {present_questions}")
    log(f"Missing questions: {missing_questions}")

    if not missing_questions:
        log("✅ No missing questions detected. Exiting script.")
        return

    random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
    log(f"Random suffix used: {random_suffix}")

    driver = ensure_driver()
    saved_cookies = cookies.copy() if cookies else {}

    try:
        # Initial navigation
        try:
            driver.get(base_url)
            wait_for_ready(driver, timeout=5)
        except Exception:
            parsed = urlparse(base_url)
            root = f"{parsed.scheme}://{parsed.netloc}/"
            driver.get(root)
            wait_for_ready(driver, timeout=5)

        if saved_cookies:
            for k, v in saved_cookies.items():
                try:
                    driver.add_cookie({"name": k, "value": v, "path": "/"})
                    log(f"Cookie added: {k}=***")
                except Exception as e:
                    log(f"Cannot add cookie {k}: {e}")

        # Loop through range
        for idx, current_id in enumerate(tqdm(range(start_id, end_id + 1), desc="IDs")):
            # Restart browser periodically
            if idx != 0 and idx % RESTART_INTERVAL == 0:
                log(f"⚡ Restarting browser after {RESTART_INTERVAL} requests to maintain speed...")
                try:
                    driver.quit()
                except Exception:
                    pass
                driver = ensure_driver()
                driver.get(base_url)
                wait_for_ready(driver, timeout=5)
                if saved_cookies:
                    for k, v in saved_cookies.items():
                        driver.add_cookie({"name": k, "value": v, "path": "/"})

            test_url = f"{base_url}{current_id}-{random_suffix}"
            attempt = 0
            while attempt < 3:
                try:
                    driver.get(test_url)
                    wait_for_ready(driver, timeout=5)
                    time.sleep(random.uniform(slow_down, slow_down + 0.6))
                    final_url = driver.current_url
                    matched = False

                    # --- Check final URL ---
                    for q in missing_questions:
                        pattern = f"{topic_prefix}question-{q}-"
                        if pattern in final_url:
                            urls_existing = load_urls()
                            if final_url not in urls_existing:
                                urls_existing.append(final_url)
                                urls_existing = sorted(urls_existing, key=lambda u: extract_question_number(u) or 9999)
                                with open(URLS_FILE, "w", encoding="utf-8") as f:
                                    for u in urls_existing:
                                        f.write(u + "\n")
                                log(f"😎 Found via final URL: {final_url}")
                            matched = True
                            break

                    # --- If not found, check HTML source ---
                    if not matched:
                        page_src = driver.page_source
                        for q in missing_questions:
                            pattern = f"{topic_prefix}question-{q}-"
                            if pattern in page_src:
                                hrefs = re.findall(
                                    r'href=["\']([^"\']*' + re.escape(pattern) + r'[^"\']*)["\']',
                                    page_src
                                )
                                if hrefs:
                                    absolute = urljoin(test_url, hrefs[0])
                                    urls_existing = load_urls()
                                    if absolute not in urls_existing:
                                        urls_existing.append(absolute)
                                        urls_existing = sorted(urls_existing, key=lambda u: extract_question_number(u) or 9999)
                                        with open(URLS_FILE, "w", encoding="utf-8") as f:
                                            for u in urls_existing:
                                                f.write(u + "\n")
                                        log(f"😎 Found via page source: {absolute}")
                                    matched = True
                                    break
                    break  # success for this URL

                except Exception as e:
                    msg = str(e).lower()
                    if any(x in msg for x in ["invalid session id", "session not created", "disconnected"]):
                        log("⚠️ Chrome session lost, restarting...")
                        try:
                            driver.quit()
                        except Exception:
                            pass
                        time.sleep(1)
                        driver = ensure_driver()
                        driver.get(base_url)
                        wait_for_ready(driver, timeout=5)
                        if saved_cookies:
                            for k, v in saved_cookies.items():
                                driver.add_cookie({"name": k, "value": v, "path": "/"})
                        attempt += 1
                    else:
                        log(f"  ↳ Selenium error visiting: {e}")
                        break

        log("\n✅ Search complete.")
    finally:
        try:
            driver.quit()
        except Exception:
            pass


# -------------------- Main --------------------
def main():
    if len(sys.argv) < 2:
        log("Usage: python complete-list.py [estimate|search <nb_questions> <start_id> <end_id> [--headless] [key=val ...]]")
        sys.exit(1)

    mode = sys.argv[1]

    if mode == "estimate":
        estimate_range()
    elif mode == "search":
        if len(sys.argv) < 5:
            log("Usage: python complete-list.py search <nb_questions> <start_id> <end_id> [--headless] [key=val ...]")
            sys.exit(1)

        nb_questions = int(sys.argv[2])
        start_id = int(sys.argv[3])
        end_id = int(sys.argv[4])
        headless = "--headless" in sys.argv

        cookie_dict = {}
        for arg in sys.argv[5:]:
            if "=" in arg and not arg.startswith("-"):
                k, v = arg.split("=", 1)
                cookie_dict[k] = v

        search_missing(nb_questions, start_id, end_id, headless=headless,
                       cookies=cookie_dict if cookie_dict else None)
    else:
        log("Unknown mode. Use 'estimate' or 'search'.")


if __name__ == "__main__":
    main()
