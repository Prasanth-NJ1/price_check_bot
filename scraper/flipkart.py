#flipkart.py
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import re
import time
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from db import add_or_update_product
from selenium.webdriver.chrome.service import Service


import platform
import shutil

def get_flipkart_price(url, user_id):
    # Cross-platform binary/driver paths
    if platform.system() == "Windows":
        chrome_binary = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
        chromedriver_path = r"C:\Users\prasa\Downloads\chromedriver-win64\chromedriver-win64\chromedriver.exe"
    else:
        chrome_binary = os.environ.get("CHROME_BIN", "/usr/bin/chromium")
        chromedriver_path = os.environ.get("CHROMEDRIVER_PATH", "/usr/bin/chromedriver")

    # Setup options
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1200,800')
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36")
    options.set_capability("browserName", "chrome")
    # ✅ Important: tell Selenium explicitly where the binary is
    options.set_capability("goog:chromeOptions", {
        "binary": chrome_binary,
        "args": options.arguments
    })

    # Debug info
    print("CHROME_BIN:", chrome_binary)
    print("CHROMEDRIVER_PATH:", chromedriver_path)

    result = {"title": "Title not found", "price": None}
    driver = None

    try:
        # Try multiple initialization paths
        try:
            print("Trying explicit chromedriver...")
            service = Service(chromedriver_path)
            driver = webdriver.Chrome(service=service, options=options)
        except Exception as driver_error:
            print(f"❌ Failed with explicit path: {str(driver_error)}")
            try:
                print("Trying with default PATH...")
                service = Service()
                driver = webdriver.Chrome(service=service, options=options)
            except Exception as fallback_error:
                print(f"❌ Failed with PATH: {str(fallback_error)}")
                print("Trying with final fallback...")
                service = Service("chromedriver")
                driver = webdriver.Chrome(service=service, options=options)

        print(f"🌐 Accessing URL: {url}")
        driver.get(url)
        time.sleep(3)

        with open("page_debug.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        print("📝 Saved page source to 'page_debug.html'")


        time.sleep(3)
        try:
            meta_tag = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//meta[@property='og:title']"))
            )
            result["title"] = meta_tag.get_attribute("content")
            print(f"Found title: {result['title']}")
        except:
            try:
                title_element = driver.find_element(By.CLASS_NAME, "B_NuCI")
                result["title"] = title_element.text.strip()
                print(f"Found title: {result['title']}")
            except:
                print("Failed to extract title")
        
        primary_selectors = [
            "div._16Jk6d", # Specific main price selector
            "div._30jeq3._16Jk6d", # Very common main price selector
            "div._30jeq3._1_WHN1", # Another common main price format
            "div._30jeq3" # General price selector
        ]
        
        for selector in primary_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                
                if elements:
                    sorted_elements = sorted(elements, key=lambda e: e.location['y'])
                    
                    for elem in sorted_elements:
                        if not elem.is_displayed():
                            continue
                            
                        price_str = elem.text.strip()
                        skip_keywords = ['off', 'emi', 'month', 'save', 'discount', 'cashback', 'extra']
                        if any(keyword.lower() in price_str.lower() for keyword in skip_keywords):
                            continue

                        price_match = re.search(r'(?:₹|Rs\.?)\s*([\d,]+)', price_str)
                        if price_match:
                            candidate_price = int(price_match.group(1).replace(",", ""))
                            if 100 <= candidate_price <= 500000:
                                result["price"] = candidate_price
                                print(f"Found price with selector {selector}: ₹{result['price']}")
                                break
                
                if result["price"] is not None:
                    break
            except Exception as e:
                print(f"Error with selector {selector}: {str(e)[:50]}")
        
        if result["price"] is None:
            try:
                price_containers = driver.find_elements(By.CSS_SELECTOR, "div.dyC4hf, div._25b18c, div._3LxTgx")
                
                for container in price_containers:
                    price_elements = container.find_elements(By.XPATH, ".//*[contains(text(), '₹') or contains(text(), 'Rs')]")
                    
                    for elem in price_elements:
                        price_str = elem.text.strip()
                        skip_keywords = ['off', 'emi', 'month', 'save', 'discount', 'cashback', 'extra']
                        if any(keyword.lower() in price_str.lower() for keyword in skip_keywords):
                            continue
                        price_match = re.search(r'(?:₹|Rs\.?)\s*([\d,]+)', price_str)
                        if price_match:
                            candidate_price = int(price_match.group(1).replace(",", ""))
                            # Validate price
                            if 100 <= candidate_price <= 500000:
                                result["price"] = candidate_price
                                print(f"Found price in container: ₹{result['price']}")
                                break
                    
                    if result["price"] is not None:
                        break
            except Exception as e:
                print(f"Error finding price in containers: {str(e)[:50]}")
        
        if result["price"] is None:
            try:
                script_elements = driver.find_elements(By.XPATH, "//script[@type='application/ld+json']")
                
                for script in script_elements:
                    script_content = script.get_attribute('innerHTML')
                    price_match = re.search(r'"price":\s*"?(\d+(?:\.\d+)?)"?', script_content)
                    if price_match:
                        candidate_price = int(float(price_match.group(1)))
                        if 100 <= candidate_price <= 500000:
                            result["price"] = candidate_price
                            print(f"Found price in structured data: ₹{result['price']}")
                            break
            except Exception as e:
                print(f"Error checking structured data: {str(e)[:50]}")
        
        if result["price"] is None:
            try:
                price_candidates = []
                price_elements = driver.find_elements(By.XPATH, "//*[contains(text(), '₹') or contains(text(), 'Rs')]")
                
                for elem in price_elements:
                    if not elem.is_displayed():
                        continue
                        
                    price_str = elem.text.strip()
                    skip_keywords = ['off', 'emi', 'month', 'save', 'discount', 'cashback', 'extra']
                    if any(keyword.lower() in price_str.lower() for keyword in skip_keywords):
                        continue

                    price_match = re.search(r'(?:₹|Rs\.?)\s*([\d,]+)', price_str)
                    if price_match:
                        candidate_price = int(price_match.group(1).replace(",", ""))

                        if 100 <= candidate_price <= 500000:
                            try:
                                font_size = elem.value_of_css_property('font-size')
                                font_size_value = float(font_size.replace('px', ''))
                            except:
                                font_size_value = 0

                            y_position = elem.location['y']
                            
                            price_candidates.append({
                                "price": candidate_price,
                                "font_size": font_size_value,
                                "y_position": y_position,
                                "element": elem
                            })
                
                if price_candidates:
                    price_candidates.sort(key=lambda x: (-x["font_size"], x["y_position"]))
                    result["price"] = price_candidates[0]["price"]
                    print(f"Found price through prominence analysis: ₹{result['price']}")
            except Exception as e:
                print(f"Error in prominence analysis: {str(e)[:50]}")
            
    except Exception as e:
        print(f"Error in scraping: {str(e)[:80]}")
    finally:
        if driver:
            driver.quit()

    if result["title"] != "Title not found" and result["price"] is not None:
        try:
            add_or_update_product(user_id, url, "flipkart", result["title"], result["price"])
            print("[DB] Product saved to MongoDB")
        except Exception as db_error:
            print(f"[DB ERROR] Failed to save to MongoDB: {db_error}")

    return result

# Example usage
if __name__ == "__main__":
    url = "https://dl.flipkart.com/s/Q_mcHqNNNN"  # Replace with your product URL
    user_id = 1897
    product_info = get_flipkart_price(url, user_id)
    print("\nFinal Results:")
    print(f"Title: {product_info['title']}")
    print(f"Price: {'₹' + str(product_info['price']) if product_info['price'] else 'Not found'}")

# import os
# import re
# import time
# import platform
# from selenium import webdriver
# from selenium.webdriver.common.by import By
# from selenium.webdriver.chrome.options import Options
# from selenium.webdriver.chrome.service import Service
# from webdriver_manager.chrome import ChromeDriverManager
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC

# import sys
# import os
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
# from db import add_or_update_product

# def get_flipkart_price(url, user_id):
#     options = Options()
#     options.add_argument('--headless=new')
#     options.add_argument('--disable-gpu')
#     options.add_argument('--no-sandbox')
#     options.add_argument('--disable-dev-shm-usage')
#     options.add_argument('--window-size=1200,800')
#     options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36")

#     # Automatically set binary path in Docker/Linux
#     if platform.system() != "Windows":
#         chrome_binary = os.getenv("CHROME_BIN", "/usr/bin/chromium")
#         options.binary_location = chrome_binary

#     print("🧪 Launching Chrome with webdriver-manager...")

#     result = {"title": "Title not found", "price": None}
#     driver = None

#     try:
#         # Let webdriver-manager handle the driver setup
#         service = Service(ChromeDriverManager().install())
#         driver = webdriver.Chrome(service=service, options=options)

#         print(f"🌐 Accessing URL: {url}")
#         driver.get(url)
#         time.sleep(3)

#         with open("page_debug.html", "w", encoding="utf-8") as f:
#             f.write(driver.page_source)
#         print("📝 Saved page source to 'page_debug.html'")

#         # Title logic
#         try:
#             title_element = WebDriverWait(driver, 10).until(
#                 EC.presence_of_element_located((By.CLASS_NAME, "B_NuCI"))
#             )
#             result["title"] = title_element.text.strip()
#             print(f"✅ Found title: {result['title']}")
#         except Exception:
#             print("⚠️ Could not find title element.")

#         # Price logic
#         try:
#             price_element = driver.find_element(By.CLASS_NAME, "_30jeq3")
#             price_text = price_element.text
#             price_match = re.search(r'₹([\d,]+)', price_text)
#             if price_match:
#                 result["price"] = int(price_match.group(1).replace(",", ""))
#                 print(f"✅ Found price: ₹{result['price']}")
#         except Exception:
#             print("⚠️ Could not find price element.")

#     except Exception as e:
#         print(f"❌ Error in scraping: {str(e)[:200]}")
#     finally:
#         if driver:
#             driver.quit()

#     # Save to DB
#     if result["title"] != "Title not found" and result["price"] is not None:
#         try:
#             add_or_update_product(user_id, url, "flipkart", result["title"], result["price"])
#             print("[DB] Product saved to MongoDB")
#         except Exception as db_error:
#             print(f"[DB ERROR] {db_error}")

#     return result

# if __name__ == "__main__":
#     url = "https://dl.flipkart.com/s/Q_mcHqNNNN"  # Replace with your product URL
#     user_id = 1897
#     product_info = get_flipkart_price(url, user_id)
#     print("\nFinal Results:")
#     print(f"Title: {product_info['title']}")
#     print(f"Price: {'₹' + str(product_info['price']) if product_info['price'] else 'Not found'}")
