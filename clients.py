#TODO: What package do I need for this client?
# How to make a request?
# That is the API endpoint?
# Any considerations?

import requests

url = "http://127.0.0.1:5055/api/items"

response = requests.get(url).json()

print(response)