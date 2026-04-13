import jwt
from datetime import datetime, timezone, timedelta

payload = {
    "sub": "admin_uuid_123",
    "username": "admin",
    "role": "admin",
    "iat": datetime.now(timezone.utc),
    "exp": datetime.now(timezone.utc) + timedelta(days=365),
    "iss": "etradie"
}
token = jwt.encode(payload, "eTradie_super_secret_for_jwt_2026", algorithm="HS256")
print(token)
