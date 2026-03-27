import requests
import time
from dotenv import load_dotenv
import os

load_dotenv()

url = "https://nextgen.owldms.com/public_api/Data"

headers = {
   "accept": "application/json",
   "X-API-Key": os.getenv("API_KEY")
}

# Gets data from the last 3 days.
params = {
   "startDate": int(time.time()) - (3 * 86400),
   # "endDate" : YOUR_END_DATE_HERE
}

response = requests.get(url, headers=headers, params=params)
data = response.json()
print(data)