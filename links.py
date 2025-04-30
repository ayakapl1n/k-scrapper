import os
import time
import random
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException, WebDriverException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from urllib.parse import urljoin

# ——— Параметры ———
START_URL                  = "https://kolesa.kz/cars/"
OUTPUT_CSV                 = "url.csv"
MAX_PAGES                  = 5000  # поставьте нужное вам число или None
AD_LINK_SELECTOR           = "a.a-card__link"
NEXT_PAGE_SELECTOR         = "a.next_page"
AD_LIST_CONTAINER_SELECTOR = "div.a-list"

# создаём папку для CSV
os.makedirs(os.path.dirname(OUTPUT_CSV), exist_ok=True)

# держим все ссылки тут
all_urls = set()

# настройка Chrome
chrome_options = ChromeOptions()
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--headless")                # запускаем без GUI
chrome_options.add_argument("--window-size=1280,800")
chrome_options.add_argument("--disable-blink-features=AutomationControlled")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument(f"user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/108.0.0.0 Safari/537.36")

driver = None

try:
    print("Setting up WebDriver...")
    service = ChromeService(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    # убираем признак automation
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    print("WebDriver setup complete.")

    current_url = START_URL
    page_count = 0

    while current_url and (MAX_PAGES is None or page_count < MAX_PAGES):
        page_count += 1
        print(f"Scraping page {page_count}: {current_url}")
        driver.get(current_url)
        # даём время подгрузиться динамике
        time.sleep(random.uniform(2, 4))

        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, AD_LIST_CONTAINER_SELECTOR))
            )

            ad_elements = driver.find_elements(By.CSS_SELECTOR, AD_LINK_SELECTOR)
            found_on_page = 0
            for elem in ad_elements:
                href = elem.get_attribute("href")
                if href:
                    absolute_url = urljoin(START_URL, href)
                    if absolute_url.startswith("https://kolesa.kz/a/show/"):
                        cleaned_url = absolute_url.split('?')[0]
                        if cleaned_url not in all_urls:
                            all_urls.add(cleaned_url)
                            found_on_page += 1

            print(f"  Found {found_on_page} ad links on this page. Total unique URLs: {len(all_urls)}")

            # пагинация
            try:
                next_btn = driver.find_element(By.CSS_SELECTOR, NEXT_PAGE_SELECTOR)
                if next_btn.is_enabled() and next_btn.is_displayed():
                    href = next_btn.get_attribute("href")
                    if href:
                        current_url = urljoin(current_url, href)
                    else:
                        next_btn.click()
                        time.sleep(2)
                        current_url = driver.current_url
                        if page_count >= MAX_PAGES or not current_url:
                            current_url = None
                else:
                    print("  No more pages.")
                    break
            except NoSuchElementException:
                print("  Next‐page button not found, ending.")
                break

        except TimeoutException:
            print("  Timeout waiting for ads container, skipping page.")
            # пропускаем страницу, но продолжаем цикл
            current_url = None
        except Exception as e:
            print(f"  Error on page {current_url}: {e}")
            current_url = None

except WebDriverException as e_wd:
    print(f"WebDriverException: {e_wd}")
except Exception as e:
    print(f"Unexpected error: {e}")
    import traceback; traceback.print_exc()
finally:
    if driver:
        print("Closing WebDriver.")
        driver.quit()

# сохраняем результат
if all_urls:
    print(f"\nFound a total of {len(all_urls)} unique URLs.")
    df = pd.DataFrame(sorted(all_urls), columns=['url'])
    df.to_csv(OUTPUT_CSV, index=False, encoding='utf-8')
    print(f"URLs saved to {OUTPUT_CSV}")
else:
    print("No URLs collected.")

print("Script finished.")
