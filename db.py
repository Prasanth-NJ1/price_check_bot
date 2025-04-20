import os
from dotenv import load_dotenv
from pymongo import MongoClient
from datetime import datetime

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)

db = client["price_tracker_bot"]
products = db["products"]

def add_or_update_product(user_id, url, site, title, price):
    
    user_id = int(user_id) if isinstance(user_id, str) else user_id
    
    now = datetime.utcnow()
    
    existing = products.find_one({"user_id": user_id, "url": url})
    
    if existing:
        print("[DB] Product already tracked, updating price history...")
        products.update_one(
            {"_id": existing["_id"]},
            {
                "$push": {
                    "price_history": {
                        "price": price,
                        "timestamp": now
                    }
                },
                "$set": {
                    "current_price": price,
                    "last_checked": now
                }
            }
        )
    else:
        print("[DB] New product, inserting...")
        new_doc = {
            "user_id": user_id,
            "url": url,
            "site": site,
            "title": title,
            "current_price": price,
            "price_history": [
                {
                    "price": price,
                    "timestamp": now
                }
            ],
            "last_checked": now
        }
        products.insert_one(new_doc)
