# price_checker.py
import logging
from datetime import datetime
import sys
import os
from dotenv import load_dotenv
from pymongo import MongoClient
from notifier import send_price_drop_alert

# Import your scrapers
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from scraper.amazon import get_amazon_price  # Update with your actual function names
from scraper.flipkart import get_flipkart_price
from scraper.myntra import get_myntra_price

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='price_checker.log'
)
logger = logging.getLogger('price_checker')

# Setup DB connection
load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client["price_tracker_bot"]
products_collection = db["products"]

def get_scraper_function(site):
    """Return the appropriate scraper function based on the site."""
    scrapers = {
        "amazon": get_amazon_price,
        "flipkart": get_flipkart_price,
        "myntra": get_myntra_price
    }
    return scrapers.get(site.lower())

def check_price(product_doc):
    """Check current price for a single product and update if changed."""
    try:
        site = product_doc["site"]
        url = product_doc["url"]
        user_id = product_doc.get("user_id", "unknown")  # Get user_id from product doc
        
        # For test product, just simulate the scrape
        if "test-product" in url:
            print(f"Test product detected: {product_doc['title']}")

            current_price = product_doc["current_price"]

            # Simulate a drop of ₹50 for testing
            new_price = current_price - 50 if current_price > 100 else current_price

            new_data = {"price": new_price, "title": product_doc["title"]}

        else:
            # Regular scraping for real products
            scraper_func = get_scraper_function(site)
            if not scraper_func:
                logger.error(f"No scraper found for site: {site}")
                return False
            
            # Get current price from website - pass user_id if needed
            new_data = scraper_func(url, user_id)
            
        new_price = new_data.get("price")
        
        if not new_price:
            logger.error(f"Failed to get price for {url}")
            return False
            
        current_price = product_doc["current_price"]
        now = datetime.utcnow()
        
        print(f"Product: {product_doc['title']}")
        print(f"Current price in DB: {current_price}")
        print(f"New price from scraper: {new_price}")
        
        # Check if price changed
        if new_price != current_price:
            print(f"PRICE CHANGE DETECTED! Old: {current_price}, New: {new_price}")
            logger.info(f"Price changed for {product_doc['title']} - Old: {current_price}, New: {new_price}")
            
            # Update price history and current price
            products_collection.update_one(
                {"_id": product_doc["_id"]},
                {
                    "$push": {
                        "price_history": {
                            "price": new_price,
                            "timestamp": now
                        }
                    },
                    "$set": {
                        "current_price": new_price,
                        "last_checked": now
                    }
                }
            )
            send_price_drop_alert(user_id,product_doc,new_price)
            return True  # Price changed
        else:
            print(f"No price change for {product_doc['title']}")
            # Just update last checked timestamp
            products_collection.update_one(
                {"_id": product_doc["_id"]},
                {"$set": {"last_checked": now}}
            )
            logger.debug(f"Price unchanged for {product_doc['title']}")
            return False  # Price unchanged
            
    except Exception as e:
        logger.error(f"Error checking price for {product_doc['url']}: {str(e)}")
        print(f"ERROR: {str(e)}")
        return False

def check_all_prices():
    """Check prices for all products in the database."""
    logger.info("Starting price check for all products")
    
    try:
        all_products = products_collection.find({})
        price_changes = 0
        products_checked = 0
        product_count = products_collection.count_documents({})
        
        print(f"Found {product_count} products in database")
        
        if product_count == 0:
            print("No products to check. Please add products first.")
            return 0
            
        for product in all_products:
            products_checked += 1
            print(f"Checking product {products_checked}/{product_count}: {product['title']} from {product['site']}")
            
            if check_price(product):
                price_changes += 1
                print(f"Price changed for {product['title']}")
            else:
                print(f"No price change for {product['title']}")
                
        logger.info(f"Price check complete. Checked {products_checked} products. Found {price_changes} price changes.")
        return price_changes
        
    except Exception as e:
        logger.error(f"Error in check_all_prices: {str(e)}")
        print(f"Error checking prices: {str(e)}")
        return 0

if __name__ == "__main__":
    # This allows you to run the price checker directly for testing
    print("Starting manual price check...")
    changes = check_all_prices()
    print(f"Price check complete. Found {changes} price changes.")