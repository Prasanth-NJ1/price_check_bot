#amazon.py
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import shutil
import platform
import re
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
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1200,800')
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36")
    options.set_capability("browserName", "chrome")
    # Cross-platform Chrome/Chromedriver setup
    if platform.system() == "Windows":
        chrome_binary = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
        chromedriver_path = r"C:\Users\prasa\Downloads\chromedriver-win64\chromedriver-win64\chromedriver.exe"
    else:
        # Use environment variables or fall back to binary name (let PATH resolve it)
        chrome_binary = os.environ.get("CHROME_BIN", "/usr/bin/chromium")
        chromedriver_path = os.environ.get("CHROMEDRIVER_PATH", "chromedriver")

    # Debug output
    print("CHROME_BIN:", chrome_binary)
    print("CHROMEDRIVER_PATH:", chromedriver_path)
    
    # Set the Chrome binary
    options.binary_location = chrome_binary
    
    result = {"title": "Title not found", "price": None}
    
    try:
        # Try to initialize the WebDriver in a more robust way
        try:
            service = Service(chromedriver_path)
            driver = webdriver.Chrome(service=service, options=options)
        except Exception as driver_error:
            print(f"Failed to initialize Chrome with explicit path: {str(driver_error)}")
            # Fall back to letting Selenium find chromedriver in PATH
            service = Service()
            driver = webdriver.Chrome(service=service, options=options)
        
        print(f"Accessing URL: {url}")
        driver.get(url)
        with open("page_debug.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        print("📝 Saved page source to 'page_debug.html'")

        
        
        # Wait for page to load
        time.sleep(3)
        
        # Try to get title
        try:
            title_element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "productTitle"))
            )
            result["title"] = title_element.text.strip()
            print(f"Found title: {result['title']}")
        except Exception as e:
            print(f"Failed to extract title using primary method: {str(e)[:50]}")
            try:
                # Try alternative title selectors
                title_selectors = [
                    "span#productTitle", 
                    "h1.a-size-large", 
                    "h1.product-title-word-break"
                ]
                
                for selector in title_selectors:
                    try:
                        title_element = driver.find_element(By.CSS_SELECTOR, selector)
                        result["title"] = title_element.text.strip()
                        print(f"Found title using selector {selector}: {result['title']}")
                        break
                    except:
                        continue
                        
                # If still no title, try meta tags
                if result["title"] == "Title not found":
                    meta_tag = driver.find_element(By.XPATH, "//meta[@name='title' or @property='og:title']")
                    result["title"] = meta_tag.get_attribute("content")
                    print(f"Found title from meta tag: {result['title']}")
            except Exception as e:
                print(f"Failed to extract title: {str(e)[:50]}")
        
        # Price extraction with multiple approaches
        price_found = False
        
        # Approach 1: Standard price selectors
        price_selectors = [
            "span.a-price span.a-offscreen",
            "span.a-price-whole",
            "#priceblock_ourprice",
            "#priceblock_dealprice",
            ".a-price .a-offscreen",
            "#price_inside_buybox",
            "span.priceToPay span.a-offscreen"
        ]
        
        for selector in price_selectors:
            if price_found:
                break
                
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                
                for elem in elements:
                    if not elem.is_displayed() and "a-offscreen" not in selector:
                        continue
                        
                    price_text = elem.text.strip()
                    if not price_text and "a-offscreen" in selector:
                        price_text = elem.get_attribute("innerHTML").strip()
                    
                    price_match = re.search(r'(?:₹|Rs\.?|INR|₹\s*|Rs\.?\s*|INR\s*)?([0-9,]+(?:\.[0-9]+)?)', price_text)
                    if price_match:
                        price_str = price_match.group(1).replace(",", "")
                        try:
                            result["price"] = int(float(price_str))
                            price_found = True
                            print(f"Found price with selector {selector}: ₹{result['price']}")
                            break
                        except:
                            continue
            except Exception as e:
                print(f"Error with selector {selector}: {str(e)[:50]}")
        
        # Approach 2: Try to find whole + fraction parts
        if not price_found:
            try:
                whole_price_elem = driver.find_element(By.CLASS_NAME, "a-price-whole")
                fraction_price_elem = driver.find_element(By.CLASS_NAME, "a-price-fraction")
                
                price_whole = whole_price_elem.text.replace(",", "").strip()
                price_fraction = fraction_price_elem.text.strip()
                
                if price_whole and price_fraction:
                    try:
                        result["price"] = int(float(f"{price_whole}.{price_fraction}"))
                        price_found = True
                        print(f"Found price with whole+fraction approach: ₹{result['price']}")
                    except:
                        pass
            except Exception as e:
                print(f"Error finding whole+fraction price: {str(e)[:50]}")
        
        # Approach 3: Check for structured data in JSON-LD scripts
        if not price_found:
            try:
                script_elements = driver.find_elements(By.XPATH, "//script[@type='application/ld+json']")
                
                for script in script_elements:
                    script_content = script.get_attribute('innerHTML')
                    price_match = re.search(r'"price":\s*"?(\d+(?:\.\d+)?)"?', script_content)
                    if price_match:
                        result["price"] = int(float(price_match.group(1)))
                        price_found = True
                        print(f"Found price in structured data: ₹{result['price']}")
                        break
            except Exception as e:
                print(f"Error checking structured data: {str(e)[:50]}")
        
        # Approach 4: Generic search for anything that looks like a price
        if not price_found:
            try:
                price_candidates = []
                price_elements = driver.find_elements(By.XPATH, 
                    "//*[contains(text(), '₹') or contains(text(), 'Rs') or contains(text(), 'INR')]")
                
                for elem in price_elements:
                    price_text = elem.text.strip()
                    if not price_text:
                        continue
                        
                    price_match = re.search(r'(?:₹|Rs\.?|INR)\s*([0-9,]+(?:\.[0-9]+)?)', price_text)
                    if price_match:
                        price_str = price_match.group(1).replace(",", "")
                        try:
                            candidate_price = int(float(price_str))
                            
                            # Filter out unrealistic prices
                            if 50 <= candidate_price <= 500000:
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
                        except:
                            continue
                
                if price_candidates:
                    # Sort by prominence (font size) and position (higher up is better)
                    price_candidates.sort(key=lambda x: (-x["font_size"], x["y_position"]))
                    result["price"] = price_candidates[0]["price"]
                    price_found = True
                    print(f"Found price through prominence analysis: ₹{result['price']}")
            except Exception as e:
                print(f"Error in generic price search: {str(e)[:50]}")
        
    except Exception as e:
        print(f"Error in scraping: {str(e)[:80]}")
    finally:
        driver.quit()
    
    # Don't save to database here - let the caller handle that
    return result

if __name__ == "__main__":
    url = "https://amzn.in/d/ezSvsED"  # or another Amazon link
    user_id = "123"
    result = get_amazon_price(url, user_id)
    print("\n🔍 Final Result:")
    print(result)
