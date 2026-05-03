import os, urllib.request, json
from dotenv import load_dotenv
load_dotenv()
account = os.getenv("MT5_METAAPI_ACCOUNT_ID")
token = os.getenv("MT5_METAAPI_TOKEN")
req = urllib.request.Request(f"https://mt-client-api-v1.new-york.agiliumtrade.ai/users/current/accounts/{account}/symbols", headers={"auth-token": token})
resp = urllib.request.urlopen(req).read().decode()
data = json.loads(resp)
print(f"Type: {type(data)}")
print(f"Length: {len(data)}")
print(f"Sample: {data[:5]}")
