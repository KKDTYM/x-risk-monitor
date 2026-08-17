#!/usr/bin/env python3
"""X 账号风险评分适配器：tweets+profile -> risk_engine.RiskEngine -> <handle>_risk_v3.json

Usage:
  python assess_x_account.py <Handle> [workspace_dir]
依赖：workspace_dir 下必须有 risk_engine.py（核心评分引擎，风险分逻辑）。
"""
import json, re, sys, os
from datetime import datetime
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


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
        "is_retweet": bool(t.get('is_retweet', False)),
        "is_reply": bool(t.get('is_reply', False)),
        "is_sensitive": bool(t.get('possibly_sensitive', False)),
        "possibly_sensitive": bool(t.get('possibly_sensitive', False)),
        "hasMedia": bool(t.get('hasMedia', False)),
        "likes": parse_int(t.get('likes', '')),
        "retweets": parse_int(t.get('retweets', '')),
        "url": t.get('url') or None,
        "raw": raw,
        "time": t.get('time', ''),
        "id": t.get('id', ''),
        "views": parse_int(t.get('views', '')),
        "source": t.get('source', ''),
    })

bio = profile_raw.get('bio', '')
_fx_loc = None
_FX_DIR = os.path.join(os.path.dirname(WS), 'fx_files')
for _fxp in [os.path.join(_FX_DIR, f'{LOWER}.json'), os.path.join(os.path.dirname(WS), f'fx_{LOWER}.json')]:
    if os.path.exists(_fxp):
        try:
            _fxu = json.load(open(_fxp, encoding='utf-8')).get('user', {})
            _loc = _fxu.get('location') or ''
            _site = (_fxu.get('website') or {}).get('url') or ''
            if _loc or _site:
                bio = (bio + '\n' + _loc + '\n' + _site).strip()
                _fx_loc = (_loc, _site)
        except Exception:
            pass
        break
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
        "statuses": profile_raw.get('statuses', 0),
        "joined": profile_raw.get('joined', ''),
        "is_sensitive": False,
        "is_blue_verified": bool(profile_raw.get('verified', False)),
        "sensitive_profile_warning": bool(profile_raw.get('sensitive_profile_warning', False)),
    },
    "recent_tweets": recent,
    "is_sensitive": False,
}

engine = RiskEngine({})
extra_data = {}
_evidence = os.path.join(DATA, f'{LOWER}_search_evidence.json')
if os.path.exists(_evidence):
    extra_data = json.load(open(_evidence, encoding='utf-8'))
    extra_data['search_visibility_tested'] = True
extra_data['handle'] = HANDLE
result = engine.assess_account(raw_data, extra_data)

# ---- 历史趋势（增量监控）：追加到 data/history/<handle>.jsonl ----
_hist_dir = os.path.join(DATA, 'history')
os.makedirs(_hist_dir, exist_ok=True)
_hist_path = os.path.join(_hist_dir, f'{LOWER}.jsonl')
_prev_score = None
if os.path.exists(_hist_path):
    for line in open(_hist_path, encoding='utf-8'):
        line = line.strip()
        if line:
            try:
                _prev_score = json.loads(line).get('score')
            except Exception:
                pass
_now = datetime.now().isoformat(timespec='seconds')
with open(_hist_path, 'a', encoding='utf-8') as f:
    f.write(json.dumps({
        "evaluated_at": _now,
        "score": result['score'],
        "level": result['level'],
        "confidence": result.get('confidence'),
        "coverage": result.get('coverage'),
        "dimensions": {k: v['risk_score'] for k, v in result['dimensions'].items()},
    }, ensure_ascii=False) + '\n')
result["meta"] = {
    "handle": f"@{HANDLE}",
    "name": profile_raw.get('name', ''),
    "tweets_analyzed": len(recent),
    "followers": followers,
    "following": following,
    "evaluated_at": datetime.now().isoformat(),
    "data_source": f"登录态深度抓取（主时间线+回复标签页）+ X embed + fxTwitter（阅读量），共 {len(recent)} 条去重（约占账号 {profile_raw.get('statuses', 0)} 条的 {len(recent)*100//max(1, profile_raw.get('statuses', 0))}%）",
    "profile_sensitive_warning": bool(profile_raw.get('sensitive_profile_warning', False)),
    "statuses": profile_raw.get('statuses', 0),
    "search_tests": extra_data,
    "impersonators": extra_data.get('impersonators', []),
    "confidence": result.get('confidence'),
    "coverage": result.get('coverage'),
    "score_range": result.get('score_range'),
    "prev_score": _prev_score,
    "engine_version": "v4.7",
}
result["tweets"] = recent

# ---- 复核落盘（v4.9）：存疑条目写入 data/review/<handle>.json ----
_review_items = []
_prohib = result["dimensions"].get("prohibited", {})
for t in _prohib.get("tier1_details", []):
    _review_items.append({"type": "Tier1", "text": t, "verdict": "pending"})
_surv = result["dimensions"].get("survival", {})
for mh in _surv.get("minor_hits", []):
    _review_items.append({"type": "幼态/未成年误判", "text": mh, "verdict": "pending"})
for dh in _surv.get("dox_hits", []):
    _review_items.append({"type": "开盒/隐私", "text": dh, "verdict": "pending"})
_review_dir = os.path.join(DATA, 'review')
if _review_items:
    os.makedirs(_review_dir, exist_ok=True)
    _rv_path = os.path.join(_review_dir, f'{LOWER}.json')
    _old_review = {}
    if os.path.exists(_rv_path):
        try:
            _old_review = json.load(open(_rv_path, encoding='utf-8'))
        except Exception:
            pass
    json.dump({
        "handle": HANDLE,
        "evaluated_at": _now,
        "status": "pending",
        "items": _review_items,
        "note": "verdict: 实锤 / 角色扮演 / 比喻 / 无法判断；AI 人工复核后回写",
    }, open(_rv_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    result["meta"]["review_pending"] = True
else:
    result["meta"]["review_pending"] = False

out_path = os.path.join(DATA, f'{LOWER}_risk.json')
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
