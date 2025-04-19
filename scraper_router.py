from scraper.amazon import get_amazon_price
from scraper.flipkart import get_flipkart_price
from scraper.myntra import get_myntra_price

def scrape_by_site(site, url, user_id):
    if site == "amazon":
        return get_amazon_price(url, user_id)
    elif site == "flipkart":
        return get_flipkart_price(url, user_id)
    elif site == "myntra":
        return get_myntra_price(url, user_id)
    else:
        return None
