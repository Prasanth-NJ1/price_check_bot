import time
from db import products, add_or_update_product
from scraper_router import scrape_by_site

def check_all_tracked_products():
    print("Checking for price updates...")

    for product in products.find():
        user_id = product["user_id"]
        url = product["url"]
        site = product["site"]
        current_price = product.get("current_price", None)
        title = product.get("title", "Unknown")

        print(f"Checking {title} ({site}) for user {user_id}...")

        # Scrape fresh data (don’t re-store yet — just fetch)
        updated_info = scrape_by_site(site, url, user_id)

        if updated_info and updated_info["price"] is not None:
            new_price = updated_info["price"]

            if new_price < current_price:
                print(f"Price dropped for {title}: ₹{current_price} → ₹{new_price}")
                #In future: send notification to Telegram here

                # Update MongoDB with new price
                add_or_update_product(user_id, url, site, updated_info["title"], new_price)
            else:
                print(f"⏸ No price drop for {title} (Current: ₹{current_price}, Scraped: ₹{new_price})")
        else:
            print(f"Failed to fetch updated price for: {title}")

def start_scheduler(interval_minutes=420):
    while True:
        check_all_tracked_products()
        print(f"Waiting {interval_minutes} minutes...\n")
        time.sleep(interval_minutes * 60)
