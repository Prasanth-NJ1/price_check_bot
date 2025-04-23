
# Price Action Notification Telegram Bot

This is a Telegram bot that helps users track product prices on Amazon, Myntra, and Flipkart. It monitors the price of each product over time and notifies the user if the current price falls below its historical average or usual price range.

## Features

- Accepts product links from Amazon, Myntra, and Flipkart  
- Analyzes historical price data for each product  
- Notifies the user when the price drops significantly  
- Stores and manages tracked products per user  
- Allows users to delete tracked items  
- Uses MongoDB Atlas for cloud storage  

## How It Works

1. **User Interaction**: Users send product links to the bot via Telegram.  
2. **Data Storage**: The bot saves the product details and the user's ID in a MongoDB Atlas database.  
3. **Price Monitoring**: The bot periodically checks prices and analyzes trends.  
4. **Notification**: If a price drop is detected, the bot sends an alert to the user.  

## Tech Stack

- Python for bot logic and scraping  
- Selenium for web scraping  
- MongoDB Atlas for database storage  
- python-telegram-bot for Telegram bot integration  

## Setup Instructions

1. **Clone the Repository**
   ```bash
   git clone https://github.com/yourusername/price-alert-telegram-bot.git
   cd price-alert-telegram-bot
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment Variables**

   Create a `.env` file and add your credentials:
   ```
   TELEGRAM_BOT_TOKEN=your_telegram_bot_token
   MONGODB_URI=your_mongodb_connection_string
   ```

4. **Run the Bot**
   ```bash
   python telegran_bot.py
   ```

 


