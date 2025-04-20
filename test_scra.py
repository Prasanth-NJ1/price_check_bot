# Create a test_scraper.py file
from price_checker import get_scraper_function

scraper = get_scraper_function("flipkart")
result = scraper("https://dl.flipkart.com/s/AVvJgauuuN", "test_user_id")
print(result)