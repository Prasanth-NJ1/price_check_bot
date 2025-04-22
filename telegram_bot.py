import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters, CallbackQueryHandler
import asyncio
import os
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import AutoReconnect, NetworkTimeout
from db import add_or_update_product
from price_checker import get_scraper_function 
from price_checker import check_all_prices, check_price, products_collection
from telegram.ext import JobQueue
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

print("✅ Telegram bot starting...")

import time
print("🕒 Time:", time.time())

import platform
print("🖥️ Platform:", platform.system())


# Then modify your database access functions to handle reconnection
def get_db_connection():
    global client, db, users_collection, products_collection
    try:
        # Test if the connection is still alive
        client.admin.command('ping')
    except (AutoReconnect, NetworkTimeout, Exception) as e:
        logger.error(f"MongoDB connection error: {e}. Reconnecting...")
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        db = client["price_tracker_bot"]
        users_collection = db["users"]
        products_collection = db["products"]
    
    return client

async def keep_db_alive(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Keep the database connection alive."""
    try:
        client = get_db_connection()
        client.admin.command('ping')
        logger.info("Database keep-alive ping successful")
    except Exception as e:
        logger.error(f"Database keep-alive error: {e}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle messages that contain a supported product URL (without using /addproduct)."""
    message_text = update.message.text
    user_id = str(update.effective_user.id)
    
    # Detect which site it is from
    site = None
    if "amazon" in message_text:
        site = "amazon"
    elif "flipkart" in message_text:
        site = "flipkart"
    elif "myntra" in message_text:
        site = "myntra"
    
    if not site:
        # Not a supported product link
        logger.info(f"Received message without recognized URL: {message_text[:30]}...")
        return

    # Let the user know we're processing it
    status = await update.message.reply_text(f"🔍 Processing your {site.capitalize()} link...")

    # Call the same scraping logic
    try:
    # Get the appropriate scraper function
        scraper_func = get_scraper_function(site)
        if not scraper_func:
            await status.edit_text(f"❌ Sorry, I couldn't find a scraper for {site}.")
            return
        
        # Fetch product details
        logger.info(f"Fetching product details for {message_text}")
        product_data = scraper_func(message_text, user_id)
        logger.info(f"Scraper result: {product_data}")
    
        if not product_data or not product_data.get("price"):
            logger.error(f"Failed to fetch product details for {message_text}. Product data: {product_data}")
            await status.edit_text(
                "❌ I couldn't fetch the product details.\n\n"
                "This could be because:\n"
                "• The URL format is incorrect\n"
                "• The product page structure changed\n"
                "• The site is blocking our request\n\n"
                "Please check the URL and try again."
            )
            return
    
    # Rest of the function...
        
        # Store the product
        title = product_data["title"]
        price = product_data["price"]
        add_or_update_product(user_id, message_text, site, title, price)

        await status.edit_text(
            f"✅ *Product added successfully!*\n\n"
            f"📦 *{title}*\n"
            f"💰 Price: ₹{price}\n"
            f"🏪 Site: {site.capitalize()}",
            parse_mode='Markdown'
        )

    except Exception as e:
        logger.error(f"Error handling message URL: {e}", exc_info=True)
        await status.edit_text(f"❌ Error processing URL: {str(e)[:100]}...\nPlease try using the /addproduct command instead.")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a welcome message when the command /start is issued."""
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name or "there"
    
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
    
    # Create keyboard with quick action buttons
    keyboard = [
        [
            InlineKeyboardButton("Add a Product ➕", callback_data="add_product_help"),
            InlineKeyboardButton("View Products 📋", callback_data="view_products")
        ],
        [
            InlineKeyboardButton("Check Prices Now 🔄", callback_data="check_prices"),
            InlineKeyboardButton("Help 🆘", callback_data="help")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f'👋 *Welcome to Price Checker, {username}!* 🛒\n\n'
        f'I\'ll help you track prices from Amazon, Flipkart, and Myntra and alert you when they drop.\n\n'
        f'*How to start:*\n'
        f'1️⃣ Add products with /addproduct [URL]\n'
        f'2️⃣ Check your products with /listproducts\n'
        f'3️⃣ Get price alerts automatically!\n\n'
        f'Need help? Use /help to see all commands.',
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle button press callbacks"""
    query = update.callback_query
    await query.answer()  # Answer the callback query to stop the loading animation
    
    if query.data == "add_product_help":
        await query.message.reply_text(
            "📝 *How to add a product:*\n\n"
            "Use the command: `/addproduct [URL]`\n\n"
            "For example:\n"
            "`/addproduct https://www.amazon.in/product-name/dp/B0ABCDEF`\n\n"
            "I support URLs from:\n"
            "• Amazon\n"
            "• Flipkart\n"
            "• Myntra",
            parse_mode='Markdown'
        )
    elif query.data == "view_products":
        # Reuse the list_products function
        await list_products(update, context)
    elif query.data == "check_prices":
        # Reuse the check_all function
        await check_all(update, context)
    elif query.data == "help":
        # Reuse the help_command function
        await help_command(update, context)

async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Subscribe user to price alerts."""
    user_id = update.effective_user.id
    
    users_collection.update_one(
        {"user_id": user_id},
        {"$set": {"subscribed": True}},
        upsert=True
    )
    logger.info(f"User {user_id} subscribed to price alerts")
    await update.message.reply_text('✅ You are now subscribed to price alerts! I\'ll notify you when prices drop.')

async def unsubscribe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Unsubscribe user from price alerts."""
    user_id = update.effective_user.id
    
    result = users_collection.update_one(
        {"user_id": user_id},
        {"$set": {"subscribed": False}}
    )
    
    if result.matched_count > 0:
        logger.info(f"User {user_id} unsubscribed from price alerts")
        await update.message.reply_text('✅ You have been unsubscribed from price alerts. You can subscribe again anytime with /subscribe.')
    else:
        await update.message.reply_text('⚠️ You are not currently registered. Use /start first to set up your account.')

async def check_all(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Manually trigger a price check for all products."""
    user_id = update.effective_user.id
    
    # Check if this is coming from a callback query
    if hasattr(update, 'callback_query'):
        chat_id = update.callback_query.message.chat_id
        message = await update.callback_query.message.reply_text("🔍 Checking prices for all products... Please wait...")
    else:
        chat_id = update.effective_chat.id
        message = await update.message.reply_text("🔍 Checking prices for all products... Please wait...")
    
    # Get count of user's products
    product_count = products_collection.count_documents({"user_id": str(user_id)})
    
    if product_count == 0:
        await message.edit_text("⚠️ You're not tracking any products yet. Add a product first with /addproduct [URL]")
        return
    
    # Call your existing price checker function
    changes = check_all_prices()
    
    if changes > 0:
        await message.edit_text(f"✅ Price check complete! Found {changes} price changes. Check your alerts for details!")
    else:
        await message.edit_text(f"✅ Price check complete! No price changes detected on your {product_count} products.")

async def list_products(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """List all products tracked by the user."""
    # Handle both direct commands and callback queries
    if hasattr(update, 'callback_query'):
        user_id = update.callback_query.from_user.id
        is_callback = True
    else:
        user_id = update.effective_user.id
        is_callback = False
    
    # Find products for this user
    user_products = products_collection.find({"user_id": str(user_id)})
    products_list = list(user_products)
    
    try:
        get_db_connection()  # Ensure connection is active
        user_products = products_collection.find({"user_id": str(user_id)})
        products_list = list(user_products)  # Convert cursor to list immediately
        
        if not products_list:
            message_text = "📭 You're not tracking any products yet.\n\nAdd your first product with:\n/addproduct [URL]"
            if is_callback:
                await update.callback_query.message.reply_text(message_text)
            else:
                await update.message.reply_text(message_text)
            return
            
        # ... rest of function ...
    except Exception as e:
        logger.error(f"Error retrieving products: {e}")
        error_message = "⚠️ There was an error retrieving your products. Please try again later."
        if is_callback:
            await update.callback_query.message.reply_text(error_message)
        else:
            await update.message.reply_text(error_message)
        return
    
    message = "📋 *Your tracked products:*\n\n"
    for idx, product in enumerate(products_list, 1):
        message += f"*{idx}. {product['title']}*\n"
        message += f"💰 Current price: ₹{product['current_price']}\n"
        
        # Show price history if available
        if 'initial_price' in product and product['initial_price'] != product['current_price']:
            if product['current_price'] < product['initial_price']:
                change = product['initial_price'] - product['current_price']
                percent = (change / product['initial_price']) * 100
                message += f"📉 Price drop: ₹{change:.2f} ({percent:.1f}%)\n"
            else:
                change = product['current_price'] - product['initial_price']
                percent = (change / product['initial_price']) * 100
                message += f"📈 Price increase: ₹{change:.2f} ({percent:.1f}%)\n"
                
        message += f"🏪 Site: {product['site'].capitalize()}\n\n"
    
    # Add action buttons
    keyboard = [
        [
            InlineKeyboardButton("Check Prices Now 🔄", callback_data="check_prices"),
            InlineKeyboardButton("Add Product ➕", callback_data="add_product_help")
        ],
        [
            InlineKeyboardButton("Delete Product 🗑️", callback_data="delete_help")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if is_callback:
        await update.callback_query.message.reply_text(message, parse_mode='Markdown', reply_markup=reply_markup)
    else:
        await update.message.reply_text(message, parse_mode='Markdown', reply_markup=reply_markup)

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
        # Show help for adding products with examples
        await update.message.reply_text(
            "📝 *How to add a product:*\n\n"
            "Please provide a product URL after the command.\n\n"
            "*Example:*\n"
            "`/addproduct https://www.amazon.in/product-name/dp/B0ABCDEF`\n\n"
            "*Supported sites:*\n"
            "• Amazon\n"
            "• Flipkart\n"
            "• Myntra",
            parse_mode='Markdown'
        )
        return
    
    url = args[0]
    
    # Auto-detect site from URL
    site = None
    if "amazon" in url or "amzn.in" in url:
        site = "amazon"
    elif "flipkart" in url:
        site = "flipkart"
    elif "myntra" in url:
        site = "myntra"
    
    if not site:
        await update.message.reply_text(
            "❌ Sorry, I couldn't detect the site from the URL.\n\n"
            "*We only support:*\n"
            "• Amazon\n"
            "• Flipkart\n"
            "• Myntra\n\n"
            "Please check your URL and try again.",
            parse_mode='Markdown'
        )
        return
    
    # Let the user know we're processing their request
    status_message = await update.message.reply_text(
        f"🔍 Adding product from {site.capitalize()}...\n"
        f"Please wait while I fetch the details..."
    )
    
    try:
        # Get the appropriate scraper function
        scraper_func = get_scraper_function(site)
        if not scraper_func:
            await status_message.edit_text(f"❌ Sorry, I couldn't find a scraper for {site}.")
            return
        
        # Fetch product details with better error handling
        try:
            loop = asyncio.get_event_loop()
            product_data = await loop.run_in_executor(None, scraper_func, url, user_id)
            await loop.run_in_executor(None, add_or_update_product, user_id, url, site, product_data["title"], product_data["price"])
        except Exception as scraper_error:
            error_msg = str(scraper_error)
            logger.error(f"Scraper error: {error_msg}", exc_info=True)
            
            if "chromedriver unexpectedly exited" in error_msg:
                await status_message.edit_text(
                    "❌ There was a problem with the web browser component.\n\n"
                    "This is a server-side issue. Please try again later."
                )
            else:
                await status_message.edit_text(
                    "❌ Sorry, there was an error adding your product.\n\n"
                    "Please check that:\n"
                    "• The URL is correct\n"
                    "• The site is supported\n"
                    "• The product is available\n\n"
                    "Try again later or contact support if the issue persists."
                )
            return
            
        if not product_data or not product_data.get("price"):
            await status_message.edit_text(
                "❌ I couldn't fetch the product details.\n\n"
                "This could be because:\n"
                "• The URL format is incorrect\n"
                "• The product page structure changed\n"
                "• The site is blocking our request\n\n"
                "Please check the URL and try again."
            )
            return
        
        # Add product to database
        title = product_data.get("title", "Unknown Product")
        price = product_data.get("price")
        
        add_or_update_product(user_id, url, site, title, price)
        
        # Success message with action buttons
        keyboard = [
            [
                InlineKeyboardButton("View All Products 📋", callback_data="view_products"),
                InlineKeyboardButton("Check Prices Now 🔄", callback_data="check_prices")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await status_message.edit_text(
            f"✅ *Product added successfully!*\n\n"
            f"📦 *{title}*\n"
            f"💰 Current Price: ₹{price}\n"
            f"🏪 Site: {site.capitalize()}\n\n"
            f"I'll notify you when the price changes!",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Error adding product: {str(e)}")
        await status_message.edit_text(
            "❌ Sorry, there was an error adding your product.\n\n"
            "Please check that:\n"
            "• The URL is correct\n"
            "• The site is supported\n"
            "• The product is available\n\n"
            "Try again later or contact support if the issue persists."
        )

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
            "🗑️ *Delete a tracked product*\n\n"
            "Please provide the product number to delete.\n"
            "Use `/listproducts` to see your products with their numbers.\n\n"
            "Example: `/deleteproduct 2` will delete your 2nd product.",
            parse_mode='Markdown'
        )
        return
    
    try:
        product_idx = int(args[0]) - 1  # Convert to 0-based index
        user_id = str(update.effective_user.id)
        
        # Get products for this user
        user_products = list(products_collection.find({"user_id": user_id}))
        
        if not user_products or product_idx >= len(user_products) or product_idx < 0:
            await update.message.reply_text(
                "❌ Invalid product number. Use `/listproducts` to see your products with correct numbers.",
                parse_mode='Markdown'
            )
            return
        
        product_to_delete = user_products[product_idx]
        
        # Delete the product
        products_collection.delete_one({"_id": product_to_delete["_id"]})
        
        # Create keyboard with action buttons
        keyboard = [
            [
                InlineKeyboardButton("View Products 📋", callback_data="view_products"),
                InlineKeyboardButton("Add Product ➕", callback_data="add_product_help")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"✅ Product *{product_to_delete['title']}* has been removed from tracking.",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
    except ValueError:
        await update.message.reply_text("❌ Please provide a valid number.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send help info when the command /help is issued."""
    help_text = """
🤖 *Price Checker Commands* 🤖

*/start* - Start the bot and register
*/subscribe* - Subscribe to price alerts
*/unsubscribe* - Unsubscribe from price alerts
*/checkall* - Check prices for all products now
*/listproducts* - Show all your tracked products
*/addproduct [url]* - Add a new product to track
*/deleteproduct [number]* - Remove a product from tracking
*/help* - Show this help message

✅ *Supported sites:*
• Amazon
• Flipkart
• Myntra

📱 *Tips:*
• Add multiple products to track more items
• Check prices manually or wait for alerts
• Share this bot with friends who love shopping!
"""
    # Add action buttons
    keyboard = [
        [
            InlineKeyboardButton("Add Product ➕", callback_data="add_product_help"),
            InlineKeyboardButton("View Products 📋", callback_data="view_products")
        ],
        [
            InlineKeyboardButton("Check Prices 🔄", callback_data="check_prices")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Handle both direct commands and callback queries
    if hasattr(update, 'callback_query'):
        await update.callback_query.message.reply_text(help_text, parse_mode='Markdown', reply_markup=reply_markup)
    else:
        await update.message.reply_text(help_text, parse_mode='Markdown', reply_markup=reply_markup)

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
    # Make commands more user-friendly by allowing them to be written differently
    application.add_handler(CommandHandler("checkall", check_all))
    application.add_handler(CommandHandler("check_all", check_all))
    application.add_handler(CommandHandler("listproducts", list_products))
    application.add_handler(CommandHandler("list_products", list_products))
    application.add_handler(CommandHandler("addproduct", add_product))
    application.add_handler(CommandHandler("add_product", add_product))
    application.add_handler(CommandHandler("deleteproduct", delete_product))
    application.add_handler(CommandHandler("delete_product", delete_product))
    
    # Add callback query handler for inline buttons
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Set up job to check prices periodically (e.g., every 6 hours)
    job_queue = application.job_queue
    job_queue.run_repeating(scheduled_check, interval=21600, first=10)
    
    # Start the Bot
    logger.info("Starting bot...")
    print("Starting Price Tracker Bot...")
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    application.run_polling()

if __name__ == '__main__':
    job_queue = JobQueue()
    job_queue.run_repeating(keep_db_alive, interval=300, first=10) 
    main()




