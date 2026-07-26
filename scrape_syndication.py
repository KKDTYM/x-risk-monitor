"""
使用 X Syndication API 抓取用户推文
无需 cookie，但可能被限流（HTTP 429）
"""
import requests
import re
import json
import time
import os

def fetch_user_tweets(username, retries=3, delay=5):
    """使用 syndication API 抓取用户推文"""
    url = f'https://syndication.twitter.com/srv/timeline-profile/screen-name/{username}'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36'
    }

    for attempt in range(retries):
        try:
            resp = requests.get(url, headers=headers, timeout=30)
            if resp.status_code == 200:
                html = resp.text
                # 提取 full_text
                matches = re.findall(r'"full_text":"([^"]{20,2000})"', html)

                # 提取日期、ID等元数据
                tweet_ids = re.findall(r'"tweet_id":"(\d+)"', html)
                dates = re.findall(r'"created_at":"([^"]+)"', html)
                media_urls = re.findall(r'"media_url":"([^"]+)"', html)

                # 提取 is_sensitive（如果有）
                # 在 HTML 中搜索 sensitive_media 标记

                # 处理推文（解码转义字符）
                tweets = []
                for i, m in enumerate(matches):
                    # JSON解码（去掉转义）
                    try:
                        text = m.encode().decode('unicode_escape')
                    except:
                        text = m
                    # 清理多余转义
                    text = text.replace('\\n', '\n').replace('\\t', ' ')
                    tweets.append({
                        'text': text,
                        'tweet_id': tweet_ids[i] if i < len(tweet_ids) else '',
                        'date': dates[i] if i < len(dates) else '',
                        'has_image': bool(media_urls[i]) if i < len(media_urls) else False,
                        'is_sensitive': False  # Syndication不返回敏感标记
                    })

                return tweets
            elif resp.status_code == 429:
                if attempt < retries - 1:
                    wait = delay * (attempt + 1)
                    print(f'  限流，等待 {wait}s 后重试...')
                    time.sleep(wait)
                continue
            else:
                print(f'  HTTP {resp.status_code}')
                return []
        except Exception as e:
            print(f'  错误: {e}')
            time.sleep(delay)

    return []

def save_account_data(username, tweets):
    """保存为引擎需要的格式"""
    data = {
        'username': username,
        'scraped_at': time.strftime('%Y-%m-%dT%H:%M:%S'),
        'source': 'syndication_api',
        'profile': {},
        'recent_tweets': [
            {
                'text': t['text'],
                'date': t['date'],
                'tweet_id': t['tweet_id'],
                'is_sensitive': t['is_sensitive'],
                'has_image': t['has_image'],
                'raw': ''  # syndication不返回HTML
            }
            for t in tweets
        ]
    }
    fname = f'F:\\Users\\Administrator\\Documents\\WorkBuddy\\2026-07-24-21-36-14\\data\\{username}_tweets_syndication.json'
    with open(fname, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f'  保存: {fname}')

if __name__ == '__main__':
    import sys
    accounts = sys.argv[1:] if len(sys.argv) > 1 else ['sunny31059']

    for acc in accounts:
        print(f'\n抓取 @{acc}...')
        tweets = fetch_user_tweets(acc)
        print(f'  获取 {len(tweets)} 条推文')
        if tweets:
            save_account_data(acc, tweets)
            # 显示前2条
            for t in tweets[:2]:
                print(f'    - {t["text"][:80]}...')
        time.sleep(2)  # 账号间间隔