#!/usr/bin/env python3
"""X 账号风险评分适配器：tweets+profile -> risk_engine.RiskEngine -> <handle>_risk_v3.json

Usage:
  python assess_x_account.py <Handle> [workspace_dir]
依赖：workspace_dir 下必须有 risk_engine.py（核心评分引擎，风险分逻辑）。
"""
import json, re, sys, os
from datetime import datetime

try:
    from risk_engine import RiskEngine
except ImportError:
    sys.path.insert(0, os.getcwd())
    from risk_engine import RiskEngine

WS = sys.argv[2] if len(sys.argv) > 2 else os.getcwd()
HANDLE = sys.argv[1]
LOWER = HANDLE.lower()
DATA = os.path.join(WS, 'data')

tweets_raw = json.load(open(os.path.join(DATA, f'{LOWER}_tweets.json'), encoding='utf-8'))
try:
    profile_raw = json.load(open(os.path.join(DATA, f'{LOWER}_profile.json'), encoding='utf-8'))
except Exception:
    profile_raw = {"name": "", "bio": "", "stats": []}


def parse_int(s):
    """解析数字，支持中文单位（万/千）和英文单位（K/M/B）"""
    if not s:
        return 0
    s = str(s)
    # 先匹配中文数字单位
    m_cn = re.search(r'([\d.]+)\s*万', s)
    if m_cn:
        return int(float(m_cn.group(1)) * 10000)
    m_q = re.search(r'([\d.]+)\s*千', s)
    if m_q:
        return int(float(m_q.group(1)) * 1000)
    # 再匹配英文单位
    m_en = re.search(r'([\d.]+)\s*([KkMmBb])', s)
    if m_en:
        val = float(m_en.group(1))
        unit = m_en.group(2).upper()
        if unit == 'K': return int(val * 1000)
        if unit == 'M': return int(val * 1000000)
        if unit == 'B': return int(val * 1000000000)
    # 纯数字
    m = re.search(r'[\d,]+', s)
    return int(m.group(0).replace(',', '')) if m else 0


recent = []
for t in tweets_raw:
    raw_text = t.get('text', '')
    raw = raw_text
    if t.get('hasMedia'):
        # 引擎判定「成人内容+媒体 -> 需标记 Sensitive Media」
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
# 中文 X 用「关注者」而非「粉丝」，正则必须覆盖
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
    "data_source": f"Playwright DOM scrape (Cookie-authorized, real @{HANDLE} timeline)",
}
result["tweets"] = recent

out_path = os.path.join(DATA, f'{LOWER}_risk_v3.json')
json.dump(result, open(out_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)

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
print(f"Saved to {out_path}")
