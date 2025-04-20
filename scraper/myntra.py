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
from webdriver_manager.chrome import ChromeDriverManager

def get_myntra_price(url,user_id):
    options = Options()
    # For production, uncomment the line below
    options.add_argument('--headless=new')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1200,800')
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36")
    # Automatically manage chromedriver
    service = Service('/usr/bin/chromedriver')  # Path to chromedriver in your Docker container
    driver = webdriver.Chrome(service=service, options=options)
    # driver = webdriver.Chrome(options=options)
    result = {"title": "Title not found", "price": None, "mrp": None, "discount": None}
    
    try:
        print(f"Accessing URL: {url}")
        driver.get(url)
        
        # Wait for page to load properly
        time.sleep(3)
        
        # Get title
        try:
            # Try to get the product title
            title_selectors = ["h1.pdp-name", "h1.pdp-title", "h1.title", ".pdp-name"]
            
            for selector in title_selectors:
                try:
                    title_element = driver.find_element(By.CSS_SELECTOR, selector)
                    if title_element:
                        result["title"] = title_element.text.strip()
                        print(f"Found title: {result['title']}")
                        break
                except:
                    continue
                    
            # If we still don't have a title, try meta tags
            if result["title"] == "Title not found":
                meta_tag = driver.find_element(By.XPATH, "//meta[@property='og:title']")
                result["title"] = meta_tag.get_attribute("content")
                print(f"Found title from meta tag: {result['title']}")
        except Exception as e:
            print(f"Failed to extract title: {str(e)[:50]}")
        
        # Approach 1: Try most common Myntra price selectors
        price_selectors = [
            "span.pdp-price strong", # Current selling price
            ".pdp-price strong",     # Alternative selling price
            ".pdp-discount-container .pdp-price strong", # Price in discount container
            "span.pdp-mrp strong",   # MRP price
            ".pdp-mrp strong",       # Alternative MRP price
            "div.pdp-price-info h1.pdp-price", # New price format
            "div.pdp-price"          # Generic price container
        ]
        
        for selector in price_selectors:
            try:
                price_elements = driver.find_elements(By.CSS_SELECTOR, selector)
                
                if price_elements:
                    for elem in price_elements:
                        price_str = elem.text.strip()
                        
                        # Extract price
                        price_match = re.search(r'(?:Rs\.|₹)?\s*([\d,]+)', price_str)
                        if price_match:
                            candidate_price = int(price_match.group(1).replace(",", ""))
                            
                            # Check if this is the main price or MRP
                            if "pdp-mrp" in selector:
                                result["mrp"] = candidate_price
                                print(f"Found MRP: ₹{result['mrp']}")
                            else:
                                result["price"] = candidate_price
                                print(f"Found price with selector {selector}: ₹{result['price']}")
                            
                            # If we found both prices, we can calculate discount
                            if result["price"] and result["mrp"]:
                                if result["mrp"] > result["price"]:
                                    discount_percentage = round(((result["mrp"] - result["price"]) / result["mrp"]) * 100)
                                    result["discount"] = discount_percentage
                                    print(f"Calculated discount: {discount_percentage}%")
                
                # If we found the selling price, we can stop looking
                if result["price"] is not None:
                    break
            except Exception as e:
                print(f"Error with selector {selector}: {str(e)[:50]}")
        
        # Approach 2: Try generic price detection
        if result["price"] is None:
            try:
                # Look for price containers
                price_containers = driver.find_elements(By.CSS_SELECTOR, "div.pdp-price-info, div.price-container")
                
                for container in price_containers:
                    # Find all text nodes within this container
                    elements = container.find_elements(By.XPATH, ".//*")
                    
                    for elem in elements:
                        elem_text = elem.text.strip()
                        if not elem_text:
                            continue
                            
                        # Look for price patterns
                        price_match = re.search(r'(?:Rs\.|₹)?\s*([\d,]+)', elem_text)
                        if price_match:
                            candidate_price = int(price_match.group(1).replace(",", ""))
                            
                            # Check if this is MRP or selling price by looking at context
                            if "mrp" in elem_text.lower() or "original" in elem_text.lower():
                                result["mrp"] = candidate_price
                                print(f"Found MRP in container: ₹{result['mrp']}")
                            else:
                                result["price"] = candidate_price
                                print(f"Found price in container: ₹{result['price']}")
                            
                            # If we found both prices, calculate discount
                            if result["price"] and result["mrp"]:
                                if result["mrp"] > result["price"]:
                                    discount_percentage = round(((result["mrp"] - result["price"]) / result["mrp"]) * 100)
                                    result["discount"] = discount_percentage
                                    print(f"Calculated discount: {discount_percentage}%")
                            
                            # If we found the selling price, we can stop
                            if result["price"] is not None:
                                break
                    
                    # If we found the selling price, we can stop
                    if result["price"] is not None:
                        break
            except Exception as e:
                print(f"Error in container analysis: {str(e)[:50]}")
        
        # Approach 3: Try to find discount info which might help infer price
        if result["price"] is None and result["mrp"] is not None:
            try:
                # Look for discount text
                discount_elements = driver.find_elements(By.CSS_SELECTOR, 
                    "span.pdp-discount, div.pdp-discount, .discount-container")
                
                for elem in discount_elements:
                    discount_text = elem.text.strip()
                    discount_match = re.search(r'(\d+)%', discount_text)
                    
                    if discount_match:
                        discount_percentage = int(discount_match.group(1))
                        result["discount"] = discount_percentage
                        
                        # If we have MRP and discount, we can calculate selling price
                        if result["mrp"]:
                            calculated_price = round(result["mrp"] * (1 - discount_percentage/100))
                            result["price"] = calculated_price
                            print(f"Calculated price from MRP and discount: ₹{result['price']}")
                            break
            except Exception as e:
                print(f"Error in discount analysis: {str(e)[:50]}")
        
        # If we still don't have a price, try one last approach with structured data
        if result["price"] is None:
            try:
                # Look for JSON-LD structured data
                script_elements = driver.find_elements(By.XPATH, "//script[@type='application/ld+json']")
                
                for script in script_elements:
                    script_content = script.get_attribute('innerHTML')
                    
                    # Look for price pattern in structured data
                    price_match = re.search(r'"price":\s*"?(\d+(?:\.\d+)?)"?', script_content)
                    if price_match:
                        result["price"] = int(float(price_match.group(1)))
                        print(f"Found price in structured data: ₹{result['price']}")
                        break
            except Exception as e:
                print(f"Error checking structured data: {str(e)[:50]}")
            
    except Exception as e:
        print(f"Error in scraping: {str(e)[:80]}")
    finally:
        driver.quit()
    
        if result["title"] != "Title not found" and result["price"] is not None:
            try:
                add_or_update_product(user_id, url, "myntra", result["title"], result["price"])
                print("[DB] Product saved to MongoDB")
            except Exception as db_error:
                print(f"[DB ERROR] Failed to save to MongoDB: {db_error}")

    
    return result

# Example usage
if __name__ == "__main__":
    url = "https://www.myntra.com/mailers/apparel-set/arrow/arrow-2-piece-slim-fit-single-breasted-formal-suit/22180132/buy?utm_source=social_share_pdp&utm_medium=deeplink&utm_campaign=social_share_pdp_deeplink"  # Replace with actual Myntra product URL
    user_id = 1972
    product_info = get_myntra_price(url,user_id)
    print("\nFinal Results:")
    print(f"Title: {product_info['title']}")
    print(f"Price: {'₹' + str(product_info['price']) if product_info['price'] else 'Not found'}")
    print(f"MRP: {'₹' + str(product_info['mrp']) if product_info['mrp'] else 'Not found'}")
    print(f"Discount: {str(product_info['discount']) + '%' if product_info['discount'] else 'Not found'}")