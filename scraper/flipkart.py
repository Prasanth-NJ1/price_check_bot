from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import re
import time
import os

def get_flipkart_price(url):
    options = Options()
    # Uncomment for production use
    # options.add_argument('--headless=new')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36")

    driver = webdriver.Chrome(options=options)
    result = {"title": "Title not found", "price": None}
    
    try:
        print(f"Accessing URL: {url}")
        driver.get(url)
        
        # Wait for page to load completely
        time.sleep(3)
        
        # Take screenshot for debugging
        screenshot_path = "flipkart_debug.png"
        driver.save_screenshot(screenshot_path)
        print(f"Screenshot saved to {os.path.abspath(screenshot_path)}")

        wait = WebDriverWait(driver, 10)
        
        # Get title
        try:
            meta_tag = wait.until(
                EC.presence_of_element_located((By.XPATH, "//meta[@property='og:title']"))
            )
            result["title"] = meta_tag.get_attribute("content")
            print(f"Found title from meta tag: {result['title']}")
        except Exception as e:
            try:
                title_element = wait.until(
                    EC.presence_of_element_located((By.CLASS_NAME, "B_NuCI"))
                )
                result["title"] = title_element.text.strip()
                print(f"Found title from page element: {result['title']}")
            except:
                print("Failed to extract title")
        
        # Debug: Save page source
        html_source = driver.page_source
        with open("flipkart_page_source.html", "w", encoding="utf-8") as f:
            f.write(html_source)
        print(f"Page source saved to {os.path.abspath('flipkart_page_source.html')}")
        
        # Approach 1: Try specific Flipkart price selectors first
        price_selectors = [
            "._30jeq3._16Jk6d",      # Most common main price selector
            "._30jeq3",               # Alternative common price selector
            ".CEmiEU",                # Another price selector
            ".dyC4hf .CEmiEU"         # Nested price structure
        ]
        
        for selector in price_selectors:
            try:
                print(f"Trying selector: {selector}")
                price_elements = driver.find_elements(By.CSS_SELECTOR, selector)
                
                if price_elements:
                    for idx, elem in enumerate(price_elements):
                        print(f"  Found element {idx+1}: {elem.text}")
                    
                    # Use the first price element that has valid price format and appears to be a main price
                    for elem in price_elements:
                        price_str = elem.text.strip()
                        
                        # Skip elements with certain keywords that indicate it's not the main price
                        skip_keywords = ['off', 'emi', 'month', 'save', 'discount', 'cashback', 'extra']
                        if any(keyword.lower() in price_str.lower() for keyword in skip_keywords):
                            print(f"  Skipping text with promotional keywords: {price_str}")
                            continue
                        
                        price_match = re.search(r'(?:₹|Rs\.?)\s*([\d,]+)', price_str)
                        if price_match:
                            result["price"] = int(price_match.group(1).replace(",", ""))
                            print(f"Found main price: ₹{result['price']}")
                            break
                    
                    if result["price"] is not None:
                        break
            except Exception as e:
                print(f"Error with selector {selector}: {str(e)[:100]}...")
        
        # Approach 2: If no specific selectors worked, try to find any price-like element
        if result["price"] is None:
            try:
                print("Trying main price detection by size and position...")
                
                # Find all price elements (containing ₹ or Rs)
                all_price_elements = driver.find_elements(By.XPATH, 
                    "//*[contains(text(), '₹') or contains(text(), 'Rs')]")
                
                # Filter out elements with promotional keywords
                filtered_elements = []
                for elem in all_price_elements:
                    elem_text = elem.text.strip()
                    skip_keywords = ['off', 'emi', 'month', 'save', 'discount', 'cashback', 'extra']
                    if not any(keyword.lower() in elem_text.lower() for keyword in skip_keywords):
                        filtered_elements.append(elem)
                        
                # Get the largest-font price element (usually the main price)
                largest_font_size = 0
                largest_font_element = None
                
                for elem in filtered_elements:
                    try:
                        font_size_str = elem.value_of_css_property('font-size')
                        font_size = float(font_size_str.replace('px', ''))
                        print(f"  Element: {elem.text} - Font size: {font_size}")
                        
                        if font_size > largest_font_size:
                            largest_font_size = font_size
                            largest_font_element = elem
                    except:
                        continue
                
                if largest_font_element is not None:
                    elem_text = largest_font_element.text.strip()
                    price_match = re.search(r'(?:₹|Rs\.?)\s*([\d,]+)', elem_text)
                    if price_match:
                        result["price"] = int(price_match.group(1).replace(",", ""))
                        print(f"Found main price by font size: ₹{result['price']}")
            except Exception as e:
                print(f"Error in main price detection: {str(e)[:100]}...")
        
        # Approach 3: Last resort - find all numbers and get the most likely price
        if result["price"] is None:
            try:
                print("Trying price detection by value analysis...")
                all_elements = driver.find_elements(By.XPATH, "//*")
                price_candidates = []
                
                for elem in all_elements:
                    try:
                        elem_text = elem.text.strip()
                        if not elem_text:
                            continue
                            
                        # Skip texts with promotional keywords
                        skip_keywords = ['off', 'emi', 'month', 'save', 'discount', 'cashback', 'extra']
                        if any(keyword.lower() in elem_text.lower() for keyword in skip_keywords):
                            continue
                        
                        # Extract prices using regex
                        price_matches = re.findall(r'(?:₹|Rs\.?)\s*([\d,]+)', elem_text)
                        for price_match in price_matches:
                            price_value = int(price_match.replace(",", ""))
                            # Only consider prices in a reasonable range (e.g., ₹500 to ₹200,000)
                            if 500 <= price_value <= 200000:
                                price_candidates.append({
                                    "price": price_value,
                                    "element": elem,
                                    "text": elem_text
                                })
                    except:
                        continue
                
                if price_candidates:
                    # Sort by price value (typically the most expensive one is the main price 
                    # if there are multiple options)
                    price_candidates.sort(key=lambda x: x["price"], reverse=True)
                    for candidate in price_candidates:
                        print(f"  Price candidate: ₹{candidate['price']} - Text: {candidate['text']}")
                    
                    # Select the first candidate (typically the most expensive one)
                    result["price"] = price_candidates[0]["price"]
                    print(f"Found main price by value analysis: ₹{result['price']}")
            except Exception as e:
                print(f"Error in price by value analysis: {str(e)[:100]}...")
            
    except Exception as e:
        print(f"Overall error in scraping: {str(e)[:150]}...")
    finally:
        driver.quit()
    
    return result

# Example usage
if __name__ == "__main__":
    url = "https://dl.flipkart.com/s/yp!!ZXNNNN"  # Your actual product URL
    product_info = get_flipkart_price(url)
    print("\nFinal Results:")
    print(f"Title: {product_info['title']}")
    print(f"Price: {'₹' + str(product_info['price']) if product_info['price'] else 'Not found'}")