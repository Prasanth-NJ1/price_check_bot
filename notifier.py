# import os
# import requests
# from dotenv import load_dotenv

# load_dotenv()
# TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# def send_price_drop_alert(user_id, product_data, new_price):
#     if not TELEGRAM_BOT_TOKEN:
#         print("[ERROR] Telegram bot token not found.")
#         return

#     old_price = product_data["current_price"]
#     title = product_data["title"]
#     url = product_data["url"]

#     message = (
#         f"*Price Drop Alert!*\n\n"
#         f"*{title}*\n"
#         f"Price dropped from ₹{old_price} to ₹{new_price}\n"
#         f"[View Product]({url})"
#     )

#     send_message(user_id, message)

# def send_message(chat_id, text):
#     url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
#     payload = {
#         "chat_id": chat_id,
#         "text": text,
#         "parse_mode": "Markdown",
#         "disable_web_page_preview": False
#     }
#     response = requests.post(url, data=payload)
#     if response.status_code != 200:
#         print(f"[ERROR] Failed to send message: {response.text}")
#     else:
#         print("Telegram message sent.")

# In notifier.py
import os
import requests
from dotenv import load_dotenv

load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

def send_price_drop_alert(user_id, product, new_price):
    """Send price drop alert to user via Telegram."""
    try:
        # Get the user's chat ID from the database
        from pymongo import MongoClient
        MONGO_URI = os.getenv("MONGO_URI")
        client = MongoClient(MONGO_URI)
        db = client["price_tracker_bot"]
        users_collection = db["users"]
        
        user = users_collection.find_one({"user_id": int(user_id)})
        
        if not user or not user.get("subscribed", False):
            print(f"User {user_id} not found or not subscribed")
            return False
            
        chat_id = user["chat_id"]
        
        # Calculate price difference and percentage
        old_price = product["current_price"]
        price_diff = old_price - new_price
        percentage = (price_diff / old_price) * 100 if old_price > 0 else 0
        
        # Format message
        message = f"*PRICE DROP ALERT!* \n\n"
        message += f"*{product['title']}*\n\n"
        message += f"*Old Price:* ₹{old_price}\n"
        message += f"*New Price:* ₹{new_price}\n"
        message += f"*You Save:* ₹{price_diff:.2f} ({percentage:.1f}%)\n\n"
        message += f"*Site:* {product['site'].capitalize()}\n"
        message += f"[View Product]({product['url']})"
        
        # Send message via Telegram API
        telegram_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "Markdown",
            "disable_web_page_preview": False
        }
        
        response = requests.post(telegram_url, json=payload)
        response.raise_for_status()
        
        print(f"Price drop alert sent to user {user_id}")
        return True
        
    except Exception as e:
        print(f"Error sending price drop alert: {str(e)}")
        return False