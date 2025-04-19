# test_price_checker.py
from pymongo import MongoClient
import os
from dotenv import load_dotenv
from datetime import datetime
from bson import ObjectId

# Load MongoDB connection
load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client["price_tracker_bot"]
products = db["products"]

def add_test_product():
    """Add a test product with initial price"""
    test_product = {
        "user_id": 12345,
        "url": "https://www.amazon.in/test-product",
        "site": "amazon",
        "title": "Test Product",
        "current_price": 1000,
        "price_history": [
            {
                "price": 1000,
                "timestamp": datetime.utcnow()
            }
        ],
        "last_checked": datetime.utcnow()
    }
    
    # Check if test product already exists
    existing = products.find_one({"url": test_product["url"]})
    if existing:
        print(f"Test product already exists with ID: {existing['_id']}")
        return existing["_id"]
    
    result = products.insert_one(test_product)
    print(f"Added test product with ID: {result.inserted_id}")
    return result.inserted_id

def change_test_product_price(product_id, new_price):
    """Simulate a price change"""
    products.update_one(
        {"_id": ObjectId(product_id)},
        {"$set": {"current_price": new_price}}
    )
    print(f"Changed test product price to {new_price}")

def get_test_product_id():
    """Get the ID of the test product or create one"""
    test_product = products.find_one({"title": "Test Product"})
    if test_product:
        return str(test_product["_id"])
    else:
        return str(add_test_product())

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python test_price_checker.py add           - Add a test product")
        print("  python test_price_checker.py change [price] - Change test product price")
        print("  python test_price_checker.py show          - Show test product details")
        sys.exit(1)
        
    command = sys.argv[1]
    
    if command == "add":
        add_test_product()
    elif command == "change":
        if len(sys.argv) < 3:
            print("Usage: python test_price_checker.py change [new_price]")
            sys.exit(1)
            
        product_id = get_test_product_id()
        new_price = int(sys.argv[2])
        print(f"Changing price for product ID: {product_id}")
        change_test_product_price(product_id, new_price)
    elif command == "show":
        product_id = get_test_product_id()
        product = products.find_one({"_id": ObjectId(product_id)})
        print(f"Test product details:")
        print(f"  ID: {product['_id']}")
        print(f"  Title: {product['title']}")
        print(f"  Current price: {product['current_price']}")
        print(f"  Last checked: {product['last_checked']}")
        print(f"  Price history: {len(product['price_history'])} entries")
    else:
        print("Unknown command. Use 'add', 'change', or 'show'")