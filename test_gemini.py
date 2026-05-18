from google import genai
key = 'AIzaSyAFkVcI_ArgUSy0RiA3eyNVAkd1jbrPPHY'
client = genai.Client(api_key=key)

candidates = [
    'gemini-flash-latest',
    'gemini-2.5-flash',
    'gemini-2.0-flash-lite',
    'gemini-3.1-flash-lite'
]

for model in candidates:
    try:
        print(f"Testing {model}...")
        resp = client.models.generate_content(model=model, contents='Say hello')
        print(f"  SUCCESS {model}: {resp.text.strip()}")
    except Exception as e:
        print(f"  FAIL {model}: {str(e)}")
