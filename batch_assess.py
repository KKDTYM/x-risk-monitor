#!/usr/bin/env python3
"""
Risk assessment script for 9 target X accounts.
Evaluates using RiskEngine, generates individual detail reports via generate_reports, and prints/stores summary.
"""
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
            # We must accurately map the raw field or content to have "https://" or "t.co/" if the tweet context suggests media exists.
            # Many times X scrapers may put media urls inside text or raw HTML or custom fields. Let's ensure 'raw' has the media signal if media exists, or simulate it.
            # In the scraper output, typically images are in raw HTML, or we can check if it's got media URLs.
            raw_str = t.get("raw", "")
            if not raw_str and ("pic.twitter.com" in t.get("text", "") or "https://" in t.get("text", "")):
                raw_str = t.get("text", "")
            # RiskEngine checks "is_sensitive", "possibly_sensitive", "is_nsfw".
            # The X scraper outputs "is_sensitive" or "possibly_sensitive" as boolean.
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
            
        # Generate HTML report
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
        
        print(f"Processed @{username}: Score={result['score']}, Level={result['level']}")

    # Print summary
    print("\n" + "=" * 50)
    print("                RISK SCAN SUMMARY")
    print("=" * 50)
    for res in summary_results:
        print(f"@{res['username']:<20} | Score: {res['score']:>3} | Level: {res['level'].upper():<8} | Tweets scraped: {res['tweets_count']}")
    
    # Save overall summary format
    summary_path = os.path.join(WS, 'batch_risk_summary.json')
    with open(summary_path, 'w', encoding='utf-8') as sf:
        json.dump(summary_results, sf, ensure_ascii=False, indent=2)
    print("=" * 50)
    print(f"Summary saved to: {summary_path}")

    # Save to data/scores.txt
    scores_dir = os.path.join(WS, 'data')
    os.makedirs(scores_dir, exist_ok=True)
    scores_path = os.path.join(scores_dir, 'scores.txt')
    with open(scores_path, 'w', encoding='utf-8') as scf:
        for res in summary_results:
            scf.write(f"@{res['username']}: Score={res['score']}, Level={res['level']}\n")
    print(f"Scores exported to: {scores_path}")

if __name__ == '__main__':
    run_assessment()
