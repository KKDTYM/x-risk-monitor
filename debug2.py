import json, urllib.request, re

WS = 'F:/Users/Administrator/Documents/WorkBuddy/2026-07-24-21-36-14'
cookies = json.load(open(f'{WS}/conny_cookies.json', encoding='utf-8'))
cookie_header = "; ".join([f"{c['name']}={c['value']}" for c in cookies])
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
HANDLE = "Maibao1998"

def get(url, headers):
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode('utf-8', 'replace')

headers = {"User-Agent": UA, "Cookie": cookie_header, "Accept-Language": "zh-CN"}
html = get(f"https://x.com/{HANDLE}", headers)
print("html len:", len(html))
print("has loginwall:", any(k in html.lower() for k in ["log in", "sign in"]) and "home" not in html.lower()[:500])
print("--- all script src (first 30) ---")
srcs = re.findall(r'src="(https://[^\"]+\.js)"', html)
for s in srcs[:30]:
    print(s)
print(f"(total {len(srcs)} script srcs)")

# try entry js for queryIds
print("\n--- probing entry js for queryIds ---")
for s in srcs[:6]:
    try:
        js = get(s, headers)
    except Exception as e:
        print("  fetch fail", s[:60], e); continue
    q1 = re.search(r'"UserByScreenName":"([a-zA-Z0-9_-]+)"', js)
    q2 = re.search(r'"UserTweets":"([a-zA-Z0-9_-]+)"', js)
    print(f"  {s.split('/')[-1][:50]}: UserByScreenName={bool(q1)} UserTweets={bool(q2)} len={len(js)}")
    if q1 and q2:
        print("  >>> FOUND qids:", q1.group(1), q2.group(1))
        break
