import urllib.request, re

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
try:
    html = urllib.request.urlopen(urllib.request.Request("https://x.com/", headers={"User-Agent": UA}), timeout=30).read().decode('utf-8', 'replace')
except Exception as e:
    print("FETCH ERROR:", e); raise SystemExit(1)
print("len:", len(html))
print("has client-web:", "client-web" in html)
print("has twimg:", "twimg" in html)
print("has loginwall:", any(k in html.lower() for k in ["log in", "sign in", "rate limit", "rate-limited"]))
print("--- first 1200 chars ---")
print(html[:1200])
print("--- abs.twimg js matches ---")
n = 0
for m in re.finditer(r'(https://[a-z.]*twimg\.com/[^\"\' ]+\.js)', html):
    print(m.group(1)[:130]); n += 1
    if n >= 5: break
if n == 0:
    print("(none)")
print("--- any src .js (first 8) ---")
n = 0
for m in list(re.finditer(r'src="([^"]+\.js)"', html)):
    print(m.group(1)[:130]); n += 1
    if n >= 8: break
