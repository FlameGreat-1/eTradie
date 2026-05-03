import os, urllib.request, json
from dotenv import load_dotenv
load_dotenv()
account = "f836cccc-4f7d-45b5-bf64-8c16224f4b2c"
token = os.getenv("MT5_METAAPI_TOKEN")
# Try client data endpoint
url = f"https://mt-client-api-v1.new-york.agiliumtrade.ai/users/current/accounts/{account}/symbols"
print(f"Querying {url}")
req = urllib.request.Request(url, headers={"auth-token": token})
try:
    resp = urllib.request.urlopen(req).read().decode()
    data = json.loads(resp)
    print(f"Type: {type(data)}")
    if isinstance(data, list):
        print(f"Length: {len(data)}")
        if len(data) > 0:
            print(f"Sample 1: {data[0]}")
            # Try to find an index symbol in the list
            indices = [s for s in data if "1000" in str(s) or "BOOM" in str(s).upper()]
            print(f"Found {len(indices)} index-like symbols: {indices[:5]}")
    else:
        print("Data:", data)
except Exception as e:
    print(f"Error: {e}")
