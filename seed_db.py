import urllib.request
import json

token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbl91dWlkXzEyMyIsInVzZXJuYW1lIjoiYWRtaW4iLCJyb2xlIjoiYWRtaW4iLCJpYXQiOjE3NzYwNDIyNjgsImV4cCI6MTgwNzU3ODI2OCwiaXNzIjoiZXRyYWRpZSJ9.0YzTH0Q_R2dLMDh6kxkYW12AQSSTh9ebnJTFI7ZOrz0"
headers = {
    "accept": "application/json",
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

# Add Gemini LLM
llm_req = urllib.request.Request(
    "http://localhost:8000/api/llm/connections",
    data=json.dumps({
        "provider": "gemini",
        "model_name": "gemini-2.5-pro",
        "api_key": "AIzaSyBQnvXmeMNg6EE8Po6SQncdciZoPHTcc4U",
        "activate": True
    }).encode(),
    headers=headers,
    method="POST"
)
try:
    with urllib.request.urlopen(llm_req) as f:
        print("Gemini Configured:", f.read().decode())
except Exception as e:
    if hasattr(e, 'read'):
        print("Gemini Error:", e.read().decode())
    else:
        print("Gemini Error:", e)
