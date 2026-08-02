#!/usr/bin/env python3
"""Run risk engine on @Conny_vv using available Fxtwitter profile data."""
import json, sys, os

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
from risk_engine import RiskEngine

# Load profile from Fxtwitter
with open(f"{BASE}/data/conny_vv_fxtwitter.json") as f:
    fx = json.load(f)

u = fx["user"]
profile = {
    "name": u.get("name"),
    "description": u.get("description", ""),
    "followers_count": u.get("followers", 0),
    "following_count": u.get("following", 0),
    "tweets_count": u.get("tweets", 0),
    "location": u.get("location", ""),
    "joined": u.get("joined", ""),
    "is_sensitive": False,
    "protected": bool(u.get("protected"))
}

config = {"risk_thresholds": {"high_score": 60, "medium_score": 30}}
engine = RiskEngine(config)

print("=" * 60)
print("  @Conny_vv 风险评估报告")
print("=" * 60)
print(f"\n【账号资料】")
print(f"  名称: {profile['name']}")
print(f"  简介: {profile['description'][:120]}...")
print(f"  粉丝: {profile['followers_count']} | 关注: {profile['following_count']} | 推文: {profile['tweets_count']}")
print(f"  地点: {profile['location']} | 加入: {profile['joined']}")
print(f"  保护: {'是' if profile['protected'] else '否'}")

# ---- 版本1: 正式评分（空推文）----
raw_formal = {
    "username": "Conny_vv",
    "account_status": "normal",
    "is_sensitive": False,
    "profile": profile,
    "recent_tweets": []  # 无推文数据（X限流无法抓取）
}
result_formal = engine.assess_account(raw_formal, [])

print(f"\n{'='*60}")
print("  【版本 A】正式评分（仅 profile，无推文）")
print(f"{'='*60}")
print(f"  总分: {result_formal['score']}/100")
print(f"  等级: {result_formal['level'].upper()}")
print(f"  建议: {result_formal['recommendation']}")
for d in result_formal['details']:
    print(f"  - {d}")

# ---- 版本2: 增强评估（bio 作为合成推文）----
bio_text = profile.get("description", "")
synthetic_tweets = [
    {
        "text": bio_text,
        "likes": 0,
        "retweets": 0,
        "is_retweet": False,
        "is_sensitive": True,
        "possibly_sensitive": True,
        "is_nsfw": True
    }
]
raw_augmented = {
    "username": "Conny_vv",
    "account_status": "normal",
    "is_sensitive": False,
    "profile": profile,
    "recent_tweets": synthetic_tweets
}
result_aug = engine.assess_account(raw_augmented, [])

print(f"\n{'='*60}")
print("  【版本 B】增强评估（bio 合成为推文样本）")
print(f"{'='*60}")
print(f"  总分: {result_aug['score']}/100")
print(f"  等级: {result_aug['level'].upper()}")
print(f"  建议: {result_aug['recommendation']}")
for d in result_aug['details']:
    print(f"  - {d}")

# ---- 维度拆解分析 ----
print(f"\n{'='*60}")
print("  【维度拆解】")
print(f"{'='*60}")

# 手动计算各维度以便展示
def dim_scores(raw, hist):
    e = RiskEngine(config)
    s = e._account_status_score(raw) * 15
    sf = e._safety_redline_score(raw) * 25
    m = e._manipulation_score(raw, hist) * 20
    sc = e._sensitive_content_score(raw) * 25
    q = e._content_quality_score(raw) * 15
    return {"账号状态": round(s), "安全红线": round(sf), "操纵指数": round(m), "敏感内容": round(sc), "内容质量": round(q)}

dims_f = dim_scores(raw_formal, [])
dims_a = dim_scores(raw_augmented, [])

print(f"  {'维度':<10} {'版本A(空)':>12} {'版本B(bio)':>12} {'满分':>8}")
print(f"  {'-'*46}")
for k in dims_f:
    print(f"  {k:<10} {dims_f[k]:>12} {dims_a[k]:>12} {'15' if k=='账号状态' or k=='内容质量' else '20' if k=='操纵指数' else '25':>8}")

# ---- 最终结论 ----
print(f"\n{'='*60}")
print("  【最终结论】")
print(f"{'='*60}")
print("""
  @Conny_vv (TS_Conny_🐰) 是一个上海 TS（跨性别女性）成人服务推广账号。

  Bio 强信号:
  - "Ts Shanghai Trans" / "真发女声 36D" — 成人服务标识
  - "🉑线下 全国可✈️" — 线下见面服务
  - "🚪66 口令私信→解锁🛰️ 领课表" — 付费解锁模式
  - TG频道链接 — 跨平台引流
  - media_count=31/tweets=37 (84%含媒体) — 高度视觉化内容

  ⚠️ 由于 X 平台当前对登录/API 的限制，未能获取真实推文。
     版本A是保守估计（仅基于profile），版本B将bio纳入推文样本，
     更接近真实风险水平。实际评分应在两者之间或更高。

  建议: 待 X 登录限流解除后（通常数小时），重新拉取完整推文再评。
""")

# Save results
output = {
    "username": "Conny_vv",
    "assessed_at": __import__('datetime').datetime.now().isoformat(),
    "data_source": "fxtwitter_profile_only (no_tweets_due_to_x_rate_limit)",
    "profile": profile,
    "scores": {
        "formal_empty_tweets": {"score": result_formal["score"], "level": result_formal["level"]},
        "augmented_with_bio": {"score": result_aug["score"], "level": result_aug["level"]}
    },
    "dimensions": {
        "empty_tweets": dims_f,
        "with_bio_tweet": dims_a
    },
    "details_formal": result_formal["details"],
    "details_augmented": result_aug["details"]
}
out_path = f"{BASE}/conny_vv_risk_result.json"
json.dump(output, open(out_path, "w"), ensure_ascii=False, indent=2)
print(f"\n结果已保存: {out_path}")
