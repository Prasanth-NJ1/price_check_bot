import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
import asyncio
import os
from dotenv import load_dotenv
from pymongo import MongoClient

from db import add_or_update_product
from price_checker import get_scraper_function  # Import the function that gets the appropriate scraper
# Import your price checker functionality
from price_checker import check_all_prices, check_price, products_collection

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    filename='telegram_bot.log'
)
logger = logging.getLogger('telegram_bot')

# Load environment variables
load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Setup DB connection (using the same connection as price_checker)
MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client["price_tracker_bot"]
users_collection = db["users"]  # Collection to store user subscription info

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a welcome message when the command /start is issued."""
    user_id = update.effective_user.id
    username = update.effective_user.username or "user"
    
    # Store user in database if not already present
    if not users_collection.find_one({"user_id": user_id}):
        users_collection.insert_one({
            "user_id": user_id,
            "username": username,
            "chat_id": update.effective_chat.id,
            "subscribed": True,
            "created_at": asyncio.get_event_loop().time()
        })
        logger.info(f"New user registered: {username} (ID: {user_id})")
    else:
        # Update chat_id in case it changed
        users_collection.update_one(
            {"user_id": user_id},
            {"$set": {"chat_id": update.effective_chat.id}}
        )
    
    await update.message.reply_text(
        f'Welcome to the Price Tracker Bot, {username}! 🛒\n\n'
        'I can help you track prices of products from Amazon, Flipkart, and Myntra.\n\n'
        'Use /subscribe to receive price alerts.\n'
        'Use /help to see all available commands.'
    )

async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Subscribe user to price alerts."""
    user_id = update.effective_user.id
    
    users_collection.update_one(
        {"user_id": user_id},
        {"$set": {"subscribed": True}},
        upsert=True
    )
    logger.info(f"User {user_id} subscribed to price alerts")
    await update.message.reply_text('You are now subscribed to price alerts!')

async def unsubscribe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Unsubscribe user from price alerts."""
    user_id = update.effective_user.id
    
    result = users_collection.update_one(
        {"user_id": user_id},
        {"$set": {"subscribed": False}}
    )
    
    if result.matched_count > 0:
        logger.info(f"User {user_id} unsubscribed from price alerts")
        await update.message.reply_text('You have been unsubscribed from price alerts.')
    else:
        await update.message.reply_text('You are not currently registered. Use /start first.')

async def check_all(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Manually trigger a price check for all products."""
    await update.message.reply_text("Checking prices for all products... This may take a moment.")
    
    # Call your existing price checker function
    changes = check_all_prices()
    
    await update.message.reply_text(f"Price check complete! Found {changes} price changes.")

async def list_products(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """List all products tracked by the user."""
    user_id = update.effective_user.id
    
    # Find products for this user
    user_products = products_collection.find({"user_id": str(user_id)})
    products_list = list(user_products)
    
    if not products_list:
        await update.message.reply_text("You're not tracking any products yet.")
        return
    
    message = "Your tracked products:\n\n"
    for idx, product in enumerate(products_list, 1):
        message += f"{idx}. {product['title']}\n"
        message += f"   Current price: ₹{product['current_price']}\n"
        message += f"   Site: {product['site']}\n\n"
    
    await update.message.reply_text(message)

# In telegram_bot.py


async def add_product(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Add a new product to track."""
    args = context.args
    user_id = str(update.effective_user.id)
    username = update.effective_user.username or "user"
    chat_id = update.effective_chat.id
    
    if not users_collection.find_one({"user_id": int(user_id)}):
        users_collection.insert_one({
            "user_id": int(user_id),
            "username": username,
            "chat_id": chat_id,
            "subscribed": True,
            "created_at": asyncio.get_event_loop().time()
        })
        logger.info(f"New user registered via add_product: {username} (ID: {user_id})")
        
    if not args:
        await update.message.reply_text(
            "Please provide a product URL.\n"
            "Usage: /add_product [product_url]"
        )
        return
    
    url = args[0]
    
    
    # Auto-detect site from URL
    site = None
    if "amazon" in url:
        site = "amazon"
    elif "flipkart" in url:
        site = "flipkart"
    elif "myntra" in url:
        site = "myntra"
    
    if not site:
        await update.message.reply_text(
            "Sorry, I couldn't detect the site from the URL. We only support Amazon, Flipkart, and Myntra at the moment."
        )
        return
    
    # Let the user know we're processing their request
    await update.message.reply_text(f"Adding product from {site.capitalize()}. Please wait while I fetch the details...")
    
    try:
        # Get the appropriate scraper function
        scraper_func = get_scraper_function(site)
        if not scraper_func:
            await update.message.reply_text(f"Sorry, I couldn't find a scraper for {site}.")
            return
        
        # Fetch product details
        product_data = scraper_func(url, user_id)
        if not product_data or not product_data.get("price"):
            await update.message.reply_text("Sorry, I couldn't fetch the product details. Please check the URL and try again.")
            return
        
        # Add product to database
        title = product_data.get("title", "Unknown Product")
        price = product_data.get("price")
        
        add_or_update_product(user_id, url, site, title, price)
        
        # Success message
        await update.message.reply_text(
            f"Product added successfully!\n\n"
            f"Title: {title}\n"
            f"Current Price: ₹{price}\n"
            f"Site: {site.capitalize()}\n\n"
            f"I'll notify you when the price changes!"
        )
        
    except Exception as e:
        logger.error(f"Error adding product: {str(e)}")
        await update.message.reply_text("Sorry, there was an error adding your product. Please try again later.")

async def scheduled_check(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Run scheduled price checks and notify subscribed users."""
    logger.info("Running scheduled price check")
    
    # Use your existing price checking function
    changes = check_all_prices()
    
    logger.info(f"Scheduled check complete. Found {changes} price changes.")
    
    # Note: The actual notifications are handled by your send_price_drop_alert function
    # which is called from within check_price in your price_checker.py

async def delete_product(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Delete a product from tracking."""
    args = context.args
    
    if not args:
        await update.message.reply_text(
            "Please provide the product number to delete.\n"
            "Use /list_products to see your products with numbers."
        )
        return
    
    try:
        product_idx = int(args[0]) - 1  # Convert to 0-based index
        user_id = str(update.effective_user.id)
        
        # Get products for this user
        user_products = list(products_collection.find({"user_id": user_id}))
        
        if not user_products or product_idx >= len(user_products) or product_idx < 0:
            await update.message.reply_text("Invalid product number. Use /list_products to see your products.")
            return
        
        product_to_delete = user_products[product_idx]
        
        # Delete the product
        products_collection.delete_one({"_id": product_to_delete["_id"]})
        
        await update.message.reply_text(f"Product '{product_to_delete['title']}' has been removed from tracking.")
        
    except ValueError:
        await update.message.reply_text("Please provide a valid number.")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send help info when the command /help is issued."""
    help_text = """
🤖 *Price Tracker Bot Commands* 🤖

/start - Start the bot and register
/subscribe - Subscribe to price alerts
/unsubscribe - Unsubscribe from price alerts
/check_all - Check prices for all products now
/list_products - Show all your tracked products
/add_product [url] - Add a new product to track
/delete_product [number] - Remove a product from tracking
/help - Show this help message

Supported sites: Amazon, Flipkart, Myntra
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')

def main() -> None:
    """Start the bot."""
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not found in environment variables")
        print("Error: TELEGRAM_BOT_TOKEN not found in environment variables")
        return
    
    # Create the Application
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("subscribe", subscribe))
    application.add_handler(CommandHandler("unsubscribe", unsubscribe))
    application.add_handler(CommandHandler("check_all", check_all))
    application.add_handler(CommandHandler("list_products", list_products))
    application.add_handler(CommandHandler("add_product", add_product))
    application.add_handler(CommandHandler("delete_product", delete_product))
    
    # Set up job to check prices periodically (e.g., every 6 hours)
    job_queue = application.job_queue
    job_queue.run_repeating(scheduled_check, interval=21600, first=10)
    
    # Start the Bot
    logger.info("Starting bot...")
    print("Starting Price Tracker Bot...")
    application.run_polling()

if __name__ == '__main__':
    main()