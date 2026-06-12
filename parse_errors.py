import json

try:
    with open('ruff_errors.json') as f:
        data = json.load(f)
    plc = [d for d in data if d['code'] == 'PLC0415']
    print(f"Total PLC0415 errors: {len(plc)}")
    for d in plc[:5]:
        print(f"{d['location']['row']}: {d['filename']}")
except Exception as e:
    print(e)
