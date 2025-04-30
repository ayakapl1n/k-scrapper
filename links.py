from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from urllib.parse import urljoin
import csv, os

START_URL         = "https://kolesa.kz/cars/almaty/"
OUTPUT_CSV        = "links.csv"
CHECKPOINT_FILE   = "checkpoint.txt"
MAX_PAGES         = 1000
AD_LINK_SELECTOR   = "a.a-card__link"

# 1) Подготовка: CSV и checkpoint
os.makedirs(os.path.dirname(OUTPUT_CSV) or ".", exist_ok=True)
if not os.path.exists(OUTPUT_CSV):
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow(["url"])

# Определяем, с какой страницы начинать
if os.path.exists(CHECKPOINT_FILE):
    with open(CHECKPOINT_FILE, "r", encoding="utf-8") as f:
        last_page = int(f.read().strip())
    start_page = last_page + 1
else:
    start_page = 1

# 2) Загружаем уже сохранённые URL, чтобы не дублировать
seen = set()
with open(OUTPUT_CSV, "r", encoding="utf-8") as f:
    reader = csv.reader(f)
    next(reader)  # пропустить заголовок
    for row in reader:
        seen.add(row[0])

with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True)
    page = browser.new_page(user_agent=(
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/108.0.0.0 Safari/537.36"
    ))

    with open(OUTPUT_CSV, "a", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)

        # 3) Основной цикл: от start_page до MAX_PAGES
        for page_num in range(start_page, MAX_PAGES + 1):
            current_url = START_URL if page_num == 1 else f"{START_URL}?page={page_num}"
            print(f"[Page {page_num}] scraping {current_url}")

            try:
                page.goto(current_url, timeout=60_000)
                page.wait_for_selector("div.a-list", timeout=15_000)
            except PlaywrightTimeout:
                print("  ⚠️ Не дождались списка объявлений — выходим.")
                break

            # Сбор ссылок
            hrefs = page.locator(AD_LINK_SELECTOR).evaluate_all(
                "els => els.map(el => el.href.split('?')[0])"
            )
            new = 0
            for href in hrefs:
                if href.startswith("https://kolesa.kz/a/show/") and href not in seen:
                    seen.add(href)
                    writer.writerow([href])
                    csvfile.flush()
                    new += 1
            print(f"  ➕ {new} новых (итого {len(seen)})")

            # 4) Сохраняем чекпоинт (текущий номер страницы)
            with open(CHECKPOINT_FILE, "w", encoding="utf-8") as f:
                f.write(str(page_num))

    browser.close()

print(f"Завершено. Отскраплено {len(seen)} ссылок. Последняя страница: {page_num}")
