# from amazon import get_amazon_price

# url = "https://amzn.in/d/5GzFTKD" 
# user_id = 182 # Use any product link
# result = get_amazon_price(url, user_id)
# print(result)



# # from flipkart import get_flipkart_price

# # url = "https://dl.flipkart.com/s/Q_mcHqNNNN"
# # data = get_flipkart_price(url)
# # print(data)

# test_amazon_scraper.py

from amazon import get_amazon_price

def test_amazon_scraper():
    url = "https://www.amazon.in/dp/B09V4M8B8R"  # Use a real product link
    user_id = "1465"

    result = get_amazon_price(url, user_id)

    print("\n🧪 Test Result:", result)

    assert result["title"] != "Title not found", "❌ Title was not found"
    assert result["price"] is not None and result["price"] > 0, "❌ Price not found or invalid"

    print("✅ Test passed: Title and price successfully extracted.")

if __name__ == "__main__":
    test_amazon_scraper()
