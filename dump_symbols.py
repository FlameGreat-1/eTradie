import os, urllib.request, json
from dotenv import load_dotenv
load_dotenv()
account = "f836cccc-4f7d-45b5-bf64-8c16224f4b2c"
token = os.getenv("MT5_METAAPI_TOKEN")
url = f"https://mt-client-api-v1.new-york.agiliumtrade.ai/users/current/accounts/{account}/symbols"
req = urllib.request.Request(url, headers={"auth-token": token})
try:
    resp = urllib.request.urlopen(req).read().decode()
    data = json.loads(resp)
    print(json.dumps(data[:100], indent=2))
except Exception as e:
    print(f"Error: {e}")
