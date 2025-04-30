from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from urllib.parse import urljoin
import csv, os

START_URL       = "https://kolesa.kz/cars/almaty/"
OUTPUT_CSV      = "links.csv"
CHECKPOINT_FILE = "checkpoint.txt"
MAX_PAGES       = 1000
LIST_SEL        = "div.a-list"
ITEM_SEL        = "a.a-card__link"

# подготовка
os.makedirs(os.path.dirname(OUTPUT_CSV) or ".", exist_ok=True)
if not os.path.exists(OUTPUT_CSV):
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow(["url"])

start_page = int(open(CHECKPOINT_FILE).read().strip()) + 1 if os.path.exists(CHECKPOINT_FILE) else 1
seen = set(row[0] for row in csv.reader(open(OUTPUT_CSV, encoding="utf-8")) if row)

with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True)
    page = browser.new_page()
    # блокируем картинки, стили и шрифты
    page.route("**/*", lambda route, req: 
        route.abort() if req.resource_type in ("image","stylesheet","font") 
        else route.continue_()
    )

    with open(OUTPUT_CSV, "a", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)

        for pg in range(start_page, MAX_PAGES+1):
            url = START_URL if pg == 1 else urljoin(START_URL, f"?page={pg}")
            print(f"[Page {pg}] → {url}")

            try:
                # ждём только DOMContentLoaded
                page.goto(url, timeout=30_000, wait_until="domcontentloaded")
                page.wait_for_selector(LIST_SEL, timeout=5_000)
            except PlaywrightTimeout:
                print(f"  ⚠️ Таймаут на странице {pg}, пропускаем.")
                with open(CHECKPOINT_FILE, "w") as f: f.write(str(pg))
                continue

            hrefs = page.locator(ITEM_SEL).evaluate_all(
                "els => els.map(e => e.href.split('?')[0])"
            )
            new = 0
            for h in hrefs:
                if h.startswith("https://kolesa.kz/a/show/") and h not in seen:
                    seen.add(h)
                    writer.writerow([h])
                    new += 1

            print(f"  ➕ {new} новых (итого {len(seen)})")
            with open(CHECKPOINT_FILE, "w") as f: f.write(str(pg))

    browser.close()

print(f"Готово: отскраплено {len(seen)} ссылок.")
