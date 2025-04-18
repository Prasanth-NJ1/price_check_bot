import requests
from bs4 import BeautifulSoup
import json
import re

def get_myntra_price_from_html(url):
    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    try:
        res = requests.get(url, headers=headers)
        if res.status_code != 200:
            print(f"[ERROR] Status code: {res.status_code}")
            return None

        soup = BeautifulSoup(res.text, 'html.parser')

        # Search for the preloaded state script
        script_tag_content = None
        for script in soup.find_all('script'):
            if script.string and 'window.__MYNTRA_PRELOADED_STATE__' in script.string:
                script_tag_content = script.string
                break

        if not script_tag_content:
            print("[ERROR] Could not find preloaded state script")
            return None

        # Extract JSON using non-greedy match
        match = re.search(r'window\.__MYNTRA_PRELOADED_STATE__\s*=\s*({.*?});\s*', script_tag_content, re.DOTALL)
        if not match:
            print("[ERROR] JSON data not found in script tag")
            return None

        json_text = match.group(1)
        json_obj = json.loads(json_text)

        # Get first product from pdp.products
        products = json_obj.get("pdp", {}).get("products", {})
        if not products:
            print("[ERROR] No products found in JSON")
            return None

        product_data = list(products.values())[0]
        title = product_data.get('name', 'N/A')
        price = product_data.get('price', {}).get('mrp', 'N/A')
        discounted = product_data.get('price', {}).get('discounted', price)

        return {'title': title, 'price': price, 'discounted_price': discounted}

    except Exception as e:
        print(f"[ERROR] JSON scraping failed: {e}")
        return None


# Test URL
url = "https://www.myntra.com/mailers/topwear/mr-bowerbird/mr-bowerbird-men-olive-green-1941-sustainable-garment-dyed-field-jacket/7825837/buy"
print(get_myntra_price_from_html(url))
