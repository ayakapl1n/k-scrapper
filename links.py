from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout, Error as PlaywrightError
from urllib.parse import urljoin
import csv, os, sys

# ——— Константы ———
START_URL       = "https://kolesa.kz/cars/almaty/"
OUTPUT_CSV      = "links.csv"
CHECKPOINT_FILE = "checkpoint.txt"
MAX_PAGES       = 1000
LIST_SEL        = "div.a-list"
LINK_SEL        = "a.a-card__link"

# ——— Подготовка файлов ———
os.makedirs(os.path.dirname(OUTPUT_CSV) or ".", exist_ok=True)
if not os.path.exists(OUTPUT_CSV):
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow(["url"])

# читаем, с какой страницы стартовать
if os.path.exists(CHECKPOINT_FILE):
    with open(CHECKPOINT_FILE, "r", encoding="utf-8") as f:
        last = f.read().strip()
        start_page = int(last) + 1 if last.isdigit() else 1
else:
    start_page = 1

# загружаем уже собранные ссылки, чтобы не дублировать
seen = set()
with open(OUTPUT_CSV, "r", encoding="utf-8") as f:
    reader = csv.reader(f)
    next(reader, None)
    for row in reader:
        if row:
            seen.add(row[0])

# ——— Основной код скрапера ———
def main():
    try:
        pw = sync_playwright().start()
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        # блокируем ресурсы, чтобы ускорить загрузку
        page.route("**/*", lambda route, req: 
            route.abort() if req.resource_type in ("image","stylesheet","font") 
            else route.continue_()
        )

        with open(OUTPUT_CSV, "a", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)

            for pg in range(start_page, MAX_PAGES + 1):
                url = START_URL if pg == 1 else urljoin(START_URL, f"?page={pg}")
                print(f"[Page {pg}] → {url}")

                # навигация + ожидание контейнера
                try:
                    page.goto(url, timeout=30_000, wait_until="domcontentloaded")
                    page.wait_for_selector(LIST_SEL, timeout=5_000)
                except (PlaywrightTimeout, PlaywrightError) as e:
                    print(f"  ⚠️ Ошибка на странице {pg}: {e!r}. Пропускаем.")
                    # сохраняем чекпоинт и идём дальше
                    with open(CHECKPOINT_FILE, "w", encoding="utf-8") as f:
                        f.write(str(pg))
                    continue
                except Exception as e:
                    print(f"  🚨 Неожиданная ошибка на {pg}: {e!r}. Пропускаем.")
                    with open(CHECKPOINT_FILE, "w", encoding="utf-8") as f:
                        f.write(str(pg))
                    continue

                # собственно сбор ссылок
                try:
                    hrefs = page.locator(LINK_SEL).evaluate_all(
                        "els => els.map(e => e.href.split('?')[0])"
                    )
                except Exception as e:
                    print(f"  ⚠️ Не удалось собрать ссылки на {pg}: {e!r}. Пропускаем.")
                    with open(CHECKPOINT_FILE, "w", encoding="utf-8") as f:
                        f.write(str(pg))
                    continue

                new = 0
                for h in hrefs:
                    if h.startswith("https://kolesa.kz/a/show/") and h not in seen:
                        seen.add(h)
                        writer.writerow([h])
                        new += 1

                print(f"  ➕ {new} новых (всего {len(seen)})")
                # обновляем checkpoint
                with open(CHECKPOINT_FILE, "w", encoding="utf-8") as f:
                    f.write(str(pg))

    finally:
        # Закрываем браузер, даже если был fatal error
        try:
            browser.close()
            pw.stop()
        except:
            pass

    print(f"Готово: всего {len(seen)} ссылок, последний page={pg}")

if __name__ == "__main__":
    main()
    # гарантируем код возврата 0, чтобы GitHub Actions перешёл к шагу Commit & Push
    sys.exit(0)
