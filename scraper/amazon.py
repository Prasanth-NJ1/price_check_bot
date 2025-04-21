# # #amazon.py
# # from selenium import webdriver
# # from selenium.webdriver.chrome.options import Options
# # from selenium.webdriver.common.by import By
# # import time
# # import sys
# # import os
# # sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
# # from db import add_or_update_product

# # def get_amazon_price(url, user_id):
# #     options = Options()
# #     options.add_argument('--headless=new')  
# #     options.add_argument('--disable-gpu')
# #     options.add_argument('--no-sandbox')
# #     options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36")


# #     driver = webdriver.Chrome(options=options)  
# #     driver.get(url)

# #     time.sleep(2)  # Let the page load

# #     try:
# #         title = driver.find_element(By.ID, "productTitle").text.strip()
# #         price_whole = driver.find_element(By.CLASS_NAME, "a-price-whole").text.replace(",", "")
# #         price_fraction = driver.find_element(By.CLASS_NAME, "a-price-fraction").text
# #         price = float(f"{price_whole}.{price_fraction}")

# #         # price = int(price_str)
# #         add_or_update_product(user_id, url, "amazon", title, price)

# #         return {
# #             "title": title,
# #             "price": price
# #         }
# #     except Exception as e:
# #         print(f"[ERROR] Couldn't fetch product info: {e}")
# #         return None
# #     finally:
# #         driver.quit()

# from selenium import webdriver
# from selenium.webdriver.chrome.options import Options
# from selenium.webdriver.chrome.service import Service
# from selenium.webdriver.common.by import By
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC
# from webdriver_manager.chrome import ChromeDriverManager

# import re
# import time
# import sys
# import os
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
# from db import add_or_update_product

# def get_amazon_price(url, user_id):
#     options = Options()
#     options.add_argument('--headless=new')
#     options.add_argument('--disable-gpu')
#     options.add_argument('--no-sandbox')
#     options.add_argument('--disable-dev-shm-usage')
#     options.add_argument('--window-size=1200,800')
#     options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36")

#     # Automatically manage chromedriver
#     service = Service(ChromeDriverManager().install())
#     driver = webdriver.Chrome(service=service, options=options)

#     # driver = webdriver.Chrome(options=options)
#     result = {"title": "Title not found", "price": None}
    
#     try:
#         print(f"Accessing URL: {url}")
#         driver.get(url)
        
#         # Wait for page to load
#         time.sleep(3)
        
#         # Try to get title
#         try:
#             title_element = WebDriverWait(driver, 10).until(
#                 EC.presence_of_element_located((By.ID, "productTitle"))
#             )
#             result["title"] = title_element.text.strip()
#             print(f"Found title: {result['title']}")
#         except Exception as e:
#             print(f"Failed to extract title using primary method: {str(e)[:50]}")
#             try:
#                 # Try alternative title selectors
#                 title_selectors = [
#                     "span#productTitle", 
#                     "h1.a-size-large", 
#                     "h1.product-title-word-break"
#                 ]
                
#                 for selector in title_selectors:
#                     try:
#                         title_element = driver.find_element(By.CSS_SELECTOR, selector)
#                         result["title"] = title_element.text.strip()
#                         print(f"Found title using selector {selector}: {result['title']}")
#                         break
#                     except:
#                         continue
                        
#                 # If still no title, try meta tags
#                 if result["title"] == "Title not found":
#                     meta_tag = driver.find_element(By.XPATH, "//meta[@name='title' or @property='og:title']")
#                     result["title"] = meta_tag.get_attribute("content")
#                     print(f"Found title from meta tag: {result['title']}")
#             except Exception as e:
#                 print(f"Failed to extract title: {str(e)[:50]}")
        
#         # Price extraction with multiple approaches
#         price_found = False
        
#         # Approach 1: Standard price selectors
#         price_selectors = [
#             "span.a-price span.a-offscreen",
#             "span.a-price-whole",
#             "#priceblock_ourprice",
#             "#priceblock_dealprice",
#             ".a-price .a-offscreen",
#             "#price_inside_buybox",
#             "span.priceToPay span.a-offscreen"
#         ]
        
#         for selector in price_selectors:
#             if price_found:
#                 break
                
#             try:
#                 elements = driver.find_elements(By.CSS_SELECTOR, selector)
                
#                 for elem in elements:
#                     if not elem.is_displayed() and "a-offscreen" not in selector:
#                         continue
                        
#                     price_text = elem.text.strip()
#                     if not price_text and "a-offscreen" in selector:
#                         price_text = elem.get_attribute("innerHTML").strip()
                    
#                     price_match = re.search(r'(?:₹|Rs\.?|INR|₹\s*|Rs\.?\s*|INR\s*)?([0-9,]+(?:\.[0-9]+)?)', price_text)
#                     if price_match:
#                         price_str = price_match.group(1).replace(",", "")
#                         try:
#                             result["price"] = int(float(price_str))
#                             price_found = True
#                             print(f"Found price with selector {selector}: ₹{result['price']}")
#                             break
#                         except:
#                             continue
#             except Exception as e:
#                 print(f"Error with selector {selector}: {str(e)[:50]}")
        
#         # Approach 2: Try to find whole + fraction parts
#         if not price_found:
#             try:
#                 whole_price_elem = driver.find_element(By.CLASS_NAME, "a-price-whole")
#                 fraction_price_elem = driver.find_element(By.CLASS_NAME, "a-price-fraction")
                
#                 price_whole = whole_price_elem.text.replace(",", "").strip()
#                 price_fraction = fraction_price_elem.text.strip()
                
#                 if price_whole and price_fraction:
#                     try:
#                         result["price"] = int(float(f"{price_whole}.{price_fraction}"))
#                         price_found = True
#                         print(f"Found price with whole+fraction approach: ₹{result['price']}")
#                     except:
#                         pass
#             except Exception as e:
#                 print(f"Error finding whole+fraction price: {str(e)[:50]}")
        
#         # Approach 3: Check for structured data in JSON-LD scripts
#         if not price_found:
#             try:
#                 script_elements = driver.find_elements(By.XPATH, "//script[@type='application/ld+json']")
                
#                 for script in script_elements:
#                     script_content = script.get_attribute('innerHTML')
#                     price_match = re.search(r'"price":\s*"?(\d+(?:\.\d+)?)"?', script_content)
#                     if price_match:
#                         result["price"] = int(float(price_match.group(1)))
#                         price_found = True
#                         print(f"Found price in structured data: ₹{result['price']}")
#                         break
#             except Exception as e:
#                 print(f"Error checking structured data: {str(e)[:50]}")
        
#         # Approach 4: Generic search for anything that looks like a price
#         if not price_found:
#             try:
#                 price_candidates = []
#                 price_elements = driver.find_elements(By.XPATH, 
#                     "//*[contains(text(), '₹') or contains(text(), 'Rs') or contains(text(), 'INR')]")
                
#                 for elem in price_elements:
#                     price_text = elem.text.strip()
#                     if not price_text:
#                         continue
                        
#                     price_match = re.search(r'(?:₹|Rs\.?|INR)\s*([0-9,]+(?:\.[0-9]+)?)', price_text)
#                     if price_match:
#                         price_str = price_match.group(1).replace(",", "")
#                         try:
#                             candidate_price = int(float(price_str))
                            
#                             # Filter out unrealistic prices
#                             if 50 <= candidate_price <= 500000:
#                                 try:
#                                     font_size = elem.value_of_css_property('font-size')
#                                     font_size_value = float(font_size.replace('px', ''))
#                                 except:
#                                     font_size_value = 0
                                    
#                                 y_position = elem.location['y']
                                
#                                 price_candidates.append({
#                                     "price": candidate_price,
#                                     "font_size": font_size_value,
#                                     "y_position": y_position,
#                                     "element": elem
#                                 })
#                         except:
#                             continue
                
#                 if price_candidates:
#                     # Sort by prominence (font size) and position (higher up is better)
#                     price_candidates.sort(key=lambda x: (-x["font_size"], x["y_position"]))
#                     result["price"] = price_candidates[0]["price"]
#                     price_found = True
#                     print(f"Found price through prominence analysis: ₹{result['price']}")
#             except Exception as e:
#                 print(f"Error in generic price search: {str(e)[:50]}")
        
#     except Exception as e:
#         print(f"Error in scraping: {str(e)[:80]}")
#     finally:
#         driver.quit()
    
#     # Save to database if we have a valid title and price
#     if result["title"] != "Title not found" and result["price"] is not None:
#         try:
#             add_or_update_product(user_id, url, "amazon", result["title"], result["price"])
#             print("[DB] Product saved to MongoDB")
#         except Exception as db_error:
#             print(f"[DB ERROR] Failed to save to MongoDB: {db_error}")
    
#     return result

# # Example usage
# if __name__ == "__main__":
#     url = "https://amzn.in/d/5GzFTKD"  # Replace with actual Amazon product URL
#     user_id = 1234
#     product_info = get_amazon_price(url, user_id)
#     print("\nFinal Results:")
#     print(f"Title: {product_info['title']}")
#     print(f"Price: {'₹' + str(product_info['price']) if product_info['price'] else 'Not found'}")


#amazon.py
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

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
    chrome_binary = os.environ.get("CHROME_BIN", "/usr/bin/chromium")
    options.binary_location = chrome_binary
    chromedriver_path = os.environ.get("CHROMEDRIVER_PATH", "/usr/bin/chromedriver")
    service = Service(chromedriver_path)
    driver = webdriver.Chrome(service=service, options=options)
    result = {"title": "Title not found", "price": None}
    
    try:
        print(f"Accessing URL: {url}")
        driver.get(url)
        
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