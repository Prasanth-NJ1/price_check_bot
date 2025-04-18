from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time

def get_amazon_price(url):
    options = Options()
    options.add_argument('--headless=new')  
    options.add_argument('--disable-gpu')

    driver = webdriver.Chrome(options=options)  
    driver.get(url)

    time.sleep(2)  # Let the page load

    try:
        title = driver.find_element(By.ID, "productTitle").text.strip()
        price_str = driver.find_element(By.CLASS_NAME, "a-price-whole").text.replace(",", "")
        price = int(price_str)

        return {
            "title": title,
            "price": price
        }
    except Exception as e:
        print(f"[ERROR] Couldn't fetch product info: {e}")
        return None
    finally:
        driver.quit()
