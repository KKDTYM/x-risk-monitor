#!/usr/bin/env python3
import json, re
from risk_engine import RiskEngine

WS = 'F:/Users/Administrator/Documents/WorkBuddy/2026-07-24-21-36-14'

tweets_raw = json.load(open(f'{WS}/data/conny_vv_tweets.json', encoding='utf-8'))
profile = json.load(open(f'{WS}/data/conny_vv_profile.json', encoding='utf-8'))

def parse_count(s, key):
    if not s: return 0
    m = re.search(rf'(\d+)\s*{key}', s)
    return int(m.group(1)) if m else 0

recent_tweets = []
for t in tweets_raw:
    recent_tweets.append({
        "text": t.get("text", ""),
        "is_retweet": False,
        "is_sensitive": False,
        "possibly_sensitive": False,
        "likes": parse_count(t.get("likes", ""), "喜欢"),
        "retweets": parse_count(t.get("retweets", ""), "转帖"),
        "original_author": "Conny_vv",
        "url": None,
    })

raw_data = {
    "account_status": "normal",
    "profile": {
        "description": profile.get("bio", ""),
        "followers_count": 447,
        "following_count": 46,
        "is_sensitive": False,
    },
    "recent_tweets": recent_tweets,
    "is_sensitive": False,
}

engine = RiskEngine({})
result = engine.assess_account(raw_data, [])

# dimension breakdown
result["dimensions"] = {
    "account_status": round(engine._account_status_score(raw_data) * 15, 1),
    "safety_redline": round(engine._safety_redline_score(raw_data) * 25, 1),
    "manipulation": round(engine._manipulation_score(raw_data, []) * 20, 1),
    "sensitive": round(engine._sensitive_content_score(raw_data) * 25, 1),
    "content_quality": round(engine._content_quality_score(raw_data) * 15, 1),
}

# attach meta
result["meta"] = {
    "handle": "@Conny_vv",
    "name": profile.get("name", ""),
    "bio": profile.get("bio", ""),
    "followers": 447,
    "following": 46,
    "tweets_analyzed": len(recent_tweets),
    "data_source": "Cookie-authorized DOM scrape (17 real tweets, 2022-07~08)",
    "scored_at": "2026-07-25",
}
result["tweets"] = recent_tweets

json.dump(result, open(f'{WS}/conny_vv_risk_real.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)

print("=== @Conny_vv RISK SCORE (real tweets) ===")
print(f"Score : {result['score']}/100  [{result['level'].upper()}]")
print(f"Dimensions:")
for k, v in result["dimensions"].items():
    print(f"  {k}: {v}")
print(f"Details:")
for d in result['details']:
    print(f"  - {d}")
print(f"\nRecommendation: {result['recommendation']}")
print(f"\nTweets analyzed: {len(recent_tweets)}")
print(f"Sample texts (3):")
for t in recent_tweets[:3]:
    print(f"  • {t['text'][:80].replace(chr(10),' ')} | ❤{t['likes']} 🔁{t['retweets']}")
