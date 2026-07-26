#!/usr/bin/env python3
import os
import sys
import json
import re
from datetime import datetime

WS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, WS)

from risk_engine import RiskEngine
from generate_reports import gen_report

accounts = [
    "sunny31059",
    "sino11680908",
    "shutiaoniang",
    "jiajia2475",
    "chichi_maddy",
    "VulpesM",
    "wuuuuuucy",
    "5277888MCHS",
    "urlittlecuteboy"
]

def parse_count(s, key):
    if not s: return 0
    if isinstance(s, int): return s
    m = re.search(r'(\d+)\s*' + key, str(s))
    return int(m.group(1)) if m else 0

def run_assessment():
    engine = RiskEngine({})
    summary_results = []
    scores_lines = []
    
    for username in accounts:
        tweet_file = os.path.join(WS, 'data', f'{username}_tweets.json')
        if not os.path.exists(tweet_file):
            print(f"[-] Data file not found for @{username}: {tweet_file}", file=sys.stderr)
            continue
            
        with open(tweet_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        profile_raw = data.get('profile', {})
        tweets_raw = data.get('recent_tweets', [])
        account_status_raw = data.get('account_status', {})
        
        # Determine status text
        astate = "normal"
        if isinstance(account_status_raw, dict):
            astate = account_status_raw.get('account_status', 'normal')
        else:
            astate = str(account_status_raw)
            
        # Parse tweets into required format
        recent_tweets = []
        for t in tweets_raw:
            raw_str = t.get("raw", "")
            if not raw_str and ("pic.twitter.com" in t.get("text", "") or "https://" in t.get("text", "")):
                raw_str = t.get("text", "")
            recent_tweets.append({
                "text": t.get("text", ""),
                "is_retweet": t.get("is_retweet", False),
                "is_sensitive": t.get("is_sensitive", False),
                "possibly_sensitive": t.get("possibly_sensitive", False),
                "is_nsfw": t.get("is_nsfw", False),
                "likes": parse_count(t.get("likes", 0), "喜欢"),
                "retweets": parse_count(t.get("retweets", 0), "转帖"),
                "original_author": username,
                "url": t.get("url", None),
                "raw": raw_str,
                "datetime": t.get("date", "")
            })
            
        # Standardize profile format
        followers_count = profile_raw.get('followers_count', 0)
        following_count = profile_raw.get('following_count', 0)
        tweets_count = profile_raw.get('tweet_count', 0)
        bio = profile_raw.get('bio', '')
        is_sensitive = profile_raw.get('is_sensitive', False)
        
        # Account formatting for RiskEngine
        raw_data = {
            "account_status": astate,
            "profile": {
                "description": bio,
                "followers_count": followers_count,
                "following_count": following_count,
                "is_sensitive": is_sensitive,
                "name": profile_raw.get('name', username),
                "tweets_count": tweets_count,
            },
            "recent_tweets": recent_tweets,
            "is_sensitive": is_sensitive,
        }
        
        # Assess
        result = engine.assess_account(raw_data, [])
        
        # Attach meta
        scored_at_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        result["meta"] = {
            "handle": f"@{username}",
            "name": profile_raw.get('name', username),
            "bio": bio,
            "followers": followers_count,
            "following": following_count,
            "tweets_analyzed": len(recent_tweets),
            "data_source": "Playwright JS Cookie-authorized Scrape",
            "scored_at": scored_at_str,
        }
        result["tweets"] = recent_tweets
        
        # Save individual result json
        risk_json_path = os.path.join(WS, 'data', f'{username}_risk_v3.json')
        with open(risk_json_path, 'w', encoding='utf-8') as jf:
            json.dump(result, jf, ensure_ascii=False, indent=2)
            
        # Generate HTML report with name {username}_rectification_v5.html
        html_content = gen_report(result)
        html_report_path = os.path.join(WS, f'{username}_rectification_v5.html')
        with open(html_report_path, 'w', encoding='utf-8') as hf:
            hf.write(html_content)
            
        summary_results.append({
            "username": username,
            "score": result["score"],
            "level": result["level"],
            "tweets_count": len(recent_tweets),
            "html_path": html_report_path
        })
        
        scores_lines.append(f"@{username}: Score={result['score']}, Level={result['level']}")
        print(f"Processed @{username}: Score={result['score']}, Level={result['level']}")
        
    # Write to F:/Users/Administrator/Documents/WorkBuddy/2026-07-24-21-36-14/data/scores.txt
    scores_file_path = os.path.join(WS, 'data', 'scores.txt')
    with open(scores_file_path, 'w', encoding='utf-8') as sf:
        sf.write("\n".join(scores_lines) + "\n")
    print(f"Scores written to {scores_file_path}")

if __name__ == '__main__':
    run_assessment()
