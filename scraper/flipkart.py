from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import requests

def resolve_flipkart_url(url):
    try:
        if "dl.flipkart.com" in url:
            r = requests.get(url, allow_redirects=True, timeout=5)
            return r.url
        return url
    except Exception as e:
        print(f"[ERROR] Failed to resolve Flipkart URL: {e}")
        return url

def get_flipkart_price(url):
    url = resolve_flipkart_url(url)

    options = Options()
    options.add_argument('--disable-gpu')  # No need for TensorFlow here
    driver = webdriver.Chrome(options=options)

    driver.get(url)

    try:
        # Wait for the title to load
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CLASS_NAME, "B_NuCI"))
        )
        
        # Attempt to close any popup (modal)
        try:
            close_button = driver.find_element(By.XPATH, "//button[contains(text(),'✕')]")
            close_button.click()
            time.sleep(1)
        except:
            print("[INFO] No popup found")
        
        # Debug: print all page elements to check for any that might not be loading
        print("[DEBUG] Page Source:\n", driver.page_source)

        # Extract the title of the product
        try:
            title = driver.find_element(By.CLASS_NAME, "B_NuCI").text.strip()
        except:
            title = driver.title
        print("[DEBUG] Title:", title)

        # Try to extract the price using multiple fallback options
        price = None
        price_classes = ["_30jeq3", "_16Jk6d", "_25b18c"]
        for cls in price_classes:
            try:
                # Wait for the price element to be visible
                price_element = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, cls))
                )
                price_str = price_element.text.strip().replace("₹", "").replace(",", "")
                price = int(price_str)
                print(f"[DEBUG] Found price: {price}")
                break
            except Exception as e:
                print(f"[ERROR] Failed to find price with class {cls}: {e}")
                continue

        if price is None:
            raise Exception("Price not found with known selectors")

        return {
            "title": title,
            "price": price
        }

    except Exception as e:
        print(f"[ERROR] Flipkart scraping failed: {e}")
        return None
    finally:
        driver.quit()
