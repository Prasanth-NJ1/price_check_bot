from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from db import add_or_update_product

def get_amazon_price(url, user_id):
    options = Options()
    options.add_argument('--headless=new')  
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')

    driver = webdriver.Chrome(options=options)  
    driver.get(url)

    time.sleep(2)  # Let the page load

    try:
        title = driver.find_element(By.ID, "productTitle").text.strip()
        price_whole = driver.find_element(By.CLASS_NAME, "a-price-whole").text.replace(",", "")
        price_fraction = driver.find_element(By.CLASS_NAME, "a-price-fraction").text
        price = float(f"{price_whole}.{price_fraction}")

        # price = int(price_str)
        add_or_update_product(user_id, url, "amazon", title, price)

        return {
            "title": title,
            "price": price
        }
    except Exception as e:
        print(f"[ERROR] Couldn't fetch product info: {e}")
        return None
    finally:
        driver.quit()
