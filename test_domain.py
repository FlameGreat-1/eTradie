from metaapi_cloud_sdk import MetaApi
import inspect

api = MetaApi("test")
try:
    print(api._metaApi._provisioningApiClient._domain)
except Exception as e:
    print(e)
