import json, re, sys
from datetime import datetime
from risk_engine import RiskEngine

WS = 'F:/Users/Administrator/Documents/WorkBuddy/2026-07-24-21-36-14'
HANDLE = sys.argv[1] if len(sys.argv) > 1 else "Maibao1998"

tweets_raw = json.load(open(f'{WS}/data/{HANDLE.lower()}_tweets.json', encoding='utf-8'))
try:
    profile_raw = json.load(open(f'{WS}/data/{HANDLE.lower()}_profile.json', encoding='utf-8'))
except Exception:
    profile_raw = {"name": "", "bio": "", "stats": []}

def parse_int(s):
    if not s:
        return 0
    m = re.search(r'[\d,]+', str(s))
    return int(m.group(0).replace(',', '')) if m else 0

recent = []
for t in tweets_raw:
    raw_text = t.get('text', '')
    raw = raw_text
    if t.get('hasMedia'):
        raw = raw_text + " https://x.com/media_item"
    recent.append({
        "text": raw_text,
        "is_retweet": False,
        "is_sensitive": bool(t.get('possibly_sensitive', False)),
        "possibly_sensitive": bool(t.get('possibly_sensitive', False)),
        "likes": parse_int(t.get('likes', '')),
        "retweets": parse_int(t.get('retweets', '')),
        "url": None,
        "raw": raw,
    })

bio = profile_raw.get('bio', '')
followers = 0
following = 0
for s in profile_raw.get('stats', []):
    if re.search(r'关注者|Followers|粉丝', s, re.I):
        followers = parse_int(s)
    elif re.search(r'正在关注|Following', s, re.I):
        following = parse_int(s)

raw_data = {
    "account_status": "normal",
    "profile": {
        "description": bio,
        "followers_count": followers,
        "following_count": following,
        "is_sensitive": False,
    },
    "recent_tweets": recent,
    "is_sensitive": False,
}

engine = RiskEngine({})
result = engine.assess_account(raw_data, [])
result["meta"] = {
    "handle": f"@{HANDLE}",
    "name": profile_raw.get('name', ''),
    "tweets_analyzed": len(recent),
    "followers": followers,
    "following": following,
    "evaluated_at": datetime.now().isoformat(),
    "data_source": "Playwright DOM scrape (Cookie-authorized, real @Maibao1998 timeline)",
}
result["tweets"] = recent

json.dump(result, open(f'{WS}/data/{HANDLE.lower()}_risk_v3.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)

print(f"=== @{HANDLE} RISK SCORE ===")
print(f"Score : {result['score']}/100  [{result['level'].upper()}]")
print("Dimensions:")
for k, v in result["dimensions"].items():
    print(f"  {k}: {v['risk_score']}/{v['max_risk']}")
print("\nDetails:")
for d in result['details']:
    print(f"  - {d}")
print(f"\nRecommendation: {result['recommendation']}")
print(f"\nTweets analyzed: {len(recent)} | followers: {followers} | following: {following}")
print(f"Saved to data/{HANDLE.lower()}_risk_v3.json")
