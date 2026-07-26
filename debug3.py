import json, urllib.request, re

WS = 'F:/Users/Administrator/Documents/WorkBuddy/2026-07-24-21-36-14'
cookies = json.load(open(f'{WS}/conny_cookies.json', encoding='utf-8'))
cookie_header = "; ".join([f"{c['name']}={c['value']}" for c in cookies])
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
headers = {"User-Agent": UA, "Cookie": cookie_header}

url = "https://abs.twimg.com/responsive-web/client-web/main.2a1d8c9a.js"
js = urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=60).read().decode('utf-8', 'replace')
open(f'{WS}/data/main.js', 'w', encoding='utf-8').write(js)
print("main.js saved, len:", len(js))

for kw in ["UserTweets", "UserByScreenName", "userByScreenName", "queryId", "graphql", "Timeline"]:
    idxs = [m.start() for m in re.finditer(re.escape(kw), js)]
    print(f"\n[{kw}] count={len(idxs)}")
    for i in idxs[:2]:
        print("   ...", js[max(0, i-100):i+100].replace("\n", " "))

# try to find any 22-char base64-ish queryId pattern near "Tweets"
print("\n--- scan for 'Tweets' substrings ---")
for m in list(re.finditer(r'[A-Za-z]+Tweets', js))[:10]:
    print("  ", m.group(0))
