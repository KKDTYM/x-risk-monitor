#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""合并深度抓取结果（主时间线 + 回复标签页）-> data/<handle>_tweets.json + profile.json

Usage:
  python merge_timelines.py <Handle> [workspace_dir] [fx_json]

规则：
- 主时间线：全部文章计入本账号时间线；作者 != handle => 本账号的转帖
- 回复标签页：仅保留作者 == handle 的回复
- 去重：主时间线优先
- profile 由 fxTwitter 公开资料生成（默认查找 <ws>/work/fx_<handle>.json）
"""
import json
import os
import re
import sys

HANDLE = sys.argv[1]
HANDLE_LOWER = HANDLE.lower()
WS = sys.argv[2] if len(sys.argv) > 2 else os.getcwd()
PD = os.path.join(WS, "data")


def find_fx():
    candidates = [
        sys.argv[3] if len(sys.argv) > 3 else "",
        os.path.join(WS, "work", f"fx_{HANDLE}.json"),
        os.path.join(WS, f"fx_{HANDLE}.json"),
        os.path.join(os.getcwd(), "work", f"fx_{HANDLE}.json"),
    ]
    for c in candidates:
        if c and os.path.exists(c):
            return c
    raise FileNotFoundError(f"fxTwitter 资料未找到：需要 fx_{HANDLE}.json（curl https://api.fxtwitter.com/{HANDLE}）")


def author_of(t):
    m = re.match(r"https://x\.com/([^/]+)/status", t.get("url") or "")
    return m.group(1).lower() if m else ""


main_raw = json.load(open(os.path.join(PD, f"{HANDLE}_deep_main.json"), encoding="utf-8"))
replies = [t for t in json.load(open(os.path.join(PD, f"{HANDLE}_deep_replies.json"), encoding="utf-8")) if author_of(t) == HANDLE_LOWER]

main = []
for t in main_raw:
    t2 = dict(t)
    t2["_src"] = "main"
    t2["_rt_author"] = author_of(t) if author_of(t) != HANDLE_LOWER else ""
    main.append(t2)
for t in replies:
    t["_src"] = "replies"
    t["_rt_author"] = ""

merged = {}
for t in main + replies:
    tid = t.get("id")
    if not tid:
        continue
    if tid not in merged or (t["_src"] == "main" and merged[tid]["_src"] == "replies"):
        merged[tid] = t

out = []
for t in merged.values():
    rt = bool(t.get("_rt_author")) or bool(t.get("is_retweet")) or bool(re.match(r"^(已转帖|Reposted)", (t.get("text") or "")))
    out.append({
        "id": t.get("id", ""),
        "text": t.get("text", ""),
        "time": t.get("time", ""),
        "likes": t.get("likes", 0),
        "retweets": t.get("retweets", 0),
        "replies": t.get("replies", 0),
        "views": t.get("views", 0),
        "bookmarks": t.get("bookmarks", 0),
        "hasMedia": bool(t.get("hasMedia", False)),
        "possibly_sensitive": bool(t.get("possibly_sensitive", False)),
        "is_retweet": rt,
        "retweet_author": t.get("_rt_author", ""),
        "is_reply": bool(t.get("is_reply", False)) or t["_src"] == "replies",
        "url": t.get("url", ""),
        "source": t["_src"],
    })
out.sort(key=lambda t: t.get("time", ""), reverse=True)

with open(os.path.join(PD, f"{HANDLE}_tweets.json"), "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)

u = json.load(open(find_fx(), encoding="utf-8")).get("user", {})
profile = {
    "name": u.get("name", ""),
    "bio": u.get("description", ""),
    "stats": [f"{u.get('followers', 0)} Followers", f"{u.get('following', 0)} Following", f"{u.get('tweets', 0)} Posts"],
    "followers": u.get("followers", 0),
    "following": u.get("following", 0),
    "statuses": u.get("tweets", 0),
    "media_count": u.get("media_count", 0),
    "verified": bool(u.get("verification", {}).get("verified")),
    "is_blue_verified": bool(u.get("verification", {}).get("verified")),
    "joined": u.get("joined", ""),
    "protected": u.get("protected", False),
    "location": u.get("location", ""),
    "website": (u.get("website") or {}).get("url", "") if isinstance(u.get("website"), dict) else u.get("website", ""),
    "sensitive_profile_warning": False,
}
with open(os.path.join(PD, f"{HANDLE}_profile.json"), "w", encoding="utf-8") as f:
    json.dump(profile, f, ensure_ascii=False, indent=2)

print(f"=== {HANDLE} ===")
print(f"unique own: {len(out)} | main-src: {sum(1 for t in out if t['source']=='main')} | replies-src: {sum(1 for t in out if t['source']=='replies')}")
print(f"posts: {sum(1 for t in out if not t['is_reply'] and not t['is_retweet'])} | replies: {sum(1 for t in out if t['is_reply'] and not t['is_retweet'])} | retweets: {sum(1 for t in out if t['is_retweet'])}")
print(f"media: {sum(1 for t in out if t['hasMedia'])} | sensitive: {sum(1 for t in out if t['possibly_sensitive'])}")
