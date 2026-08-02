import json
with open('config.json', 'r', encoding='utf-8') as f:
    c = json.load(f)
    print(json.dumps(c.get('notifications', {}), indent=2))
