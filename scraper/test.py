from amazon import get_amazon_price

url = "https://amzn.in/d/5GzFTKD" 
user_id = 182 # Use any product link
result = get_amazon_price(url, user_id)
print(result)



# from flipkart import get_flipkart_price

# url = "https://dl.flipkart.com/s/Q_mcHqNNNN"
# data = get_flipkart_price(url)
# print(data)
