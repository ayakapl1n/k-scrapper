from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from urllib.parse import urljoin
import csv, os, time, random

# ——— Константы ———
START_URL             = "https://kolesa.kz/cars/almaty/"
OUTPUT_CSV            = "links.csv"
CHECKPOINT_FILE       = "checkpoint.txt"
MAX_PAGES             = 1000
AD_LIST_CONTAINER     = "div.a-list"
AD_LINK_SELECTOR      = "a.a-card__link"

# ——— Подготовка CSV и чекпоинта ———
os.makedirs(os.path.dirname(OUTPUT_CSV) or ".", exist_ok=True)
if not os.path.exists(OUTPUT_CSV):
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow(["url"])

# откуда начинаем?
if os.path.exists(CHECKPOINT_FILE):
    with open(CHECKPOINT_FILE, "r", encoding="utf-8") as f:
        start_page = int(f.read().strip()) + 1
else:
    start_page = 1

# загружаем уже найденные ссылки, чтобы не дублировать
seen = set()
with open(OUTPUT_CSV, "r", encoding="utf-8") as f:
    reader = csv.reader(f)
    next(reader)
    for row in reader:
        seen.add(row[0])

# ——— Запуск Playwright ———
with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True)
    page = browser.new_page(user_agent=(
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/108.0.0.0 Safari/537.36"
    ))

    with open(OUTPUT_CSV, "a", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)

        for page_num in range(start_page, MAX_PAGES + 1):
            # формируем URL: для page 1 – стартовый, иначе ?page=N
            if page_num == 1:
                current_url = START_URL
            else:
                current_url = urljoin(START_URL, f"?page={page_num}")

            print(f"[Page {page_num}] → {current_url}")
            try:
                page.goto(current_url, timeout=60_000)
                page.wait_for_selector(AD_LIST_CONTAINER, timeout=15_000)
                # небольшой рандом-сап
                time.sleep(random.uniform(1, 2))

            except PlaywrightTimeout:
                print(f"  ⚠️ Таймаут на странице {page_num}, пропускаем дальше.")
                # сохраняем чекпоинт и идём дальше
                with open(CHECKPOINT_FILE, "w", encoding="utf-8") as f:
                    f.write(str(page_num))
                continue

            except Exception as e:
                print(f"  🚨 Ошибка на странице {page_num}: {e!r}, пропускаем дальше.")
                with open(CHECKPOINT_FILE, "w", encoding="utf-8") as f:
                    f.write(str(page_num))
                continue

            # ——— Сбор ссылок ———
            hrefs = page.locator(AD_LINK_SELECTOR).evaluate_all(
                "els => els.map(el => el.href.split('?')[0])"
            )
            new_count = 0
            for href in hrefs:
                if href.startswith("https://kolesa.kz/a/show/") and href not in seen:
                    seen.add(href)
                    writer.writerow([href])
                    csvfile.flush()
                    new_count += 1

            print(f"  ➕ {new_count} новых (всего {len(seen)})")

            # ——— Обновляем чекпоинт после успешного сбора ———
            with open(CHECKPOINT_FILE, "w", encoding="utf-8") as f:
                f.write(str(page_num))

    browser.close()

print(f"Готово. Собрано {len(seen)} уникальных ссылок. Последняя обработанная страница: {page_num}")
