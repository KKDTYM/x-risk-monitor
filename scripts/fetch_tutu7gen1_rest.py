"""
尝试 REST API 方式获取推文
"""
import json
import requests
from datetime import datetime

PROJECT_DIR = r'F:\Users\Administrator\Documents\WorkBuddy\2026-07-24-21-36-14'
DATA_DIR = f'{PROJECT_DIR}/data'

COOKIES_STR = '; '.join([
    "auth_token=0555da63fcf228b97af5aec8c8ed4fd6d5841880",
    "guest_id=v1%3A178505847748990053",
    "twid=u%3D2081335439026421760",
    "_twitter_sess=BAh7BiIKZmxhc2hJQzonQWN0aW9uQ29udHJvbGxlcjo6Rmxhc2g6OkZsYXNo%250ASGFzaHsABjoKQHVzZWR7AA%253D%253D--1164b91ac812d853b877e93ddb612b7471bebc74",
    "auth_multi=\"497862683:443bd09a5c16b0d8e346459f52686dc7be306564|1919756553915428864:a40bfcf10aa9fda18b4e1768fc6d63e567a9e5fc|1969781334114455552:3fe146efd1cc10b8179ef91e36f583d60a5c6e5b\"",
    "__cf_bm=gC8t1L9RsF3ndSQTlNW44GTP2fH6WB_86U2pvCjlV0U-1785063263.959605-1.0.1.1-D4toXEYknP5RJOyGlG4sM_HGw_2jhgUL6VTmOmum3utpnst26y3miE8TIaLHHRcRuu3qv8JqEVPNwzCXxdysjZc5qHIsdtkUpC0.rWlSzPWSCfviWn93gZVSUwcOiu3D",
    "ct0=bb33543802aefbd7f6b2496ef8ec78ec578d22decbc0b5a0fa2ff1d66846a7a57deff1cc2b0fbc16f7e3edb3b2bcb9b0758b128c9af16bf0133c44980671ba5f329812ffb971fdd03443edf83423e4ee",
    "kdt=I26qcLfGtmQPKocgpIA1CmOPLRiS2kYQu8CY2vdA",
    "personalization_id=\"v1_VF7XpjNa6DEkBMUivBb/xQ==\"",
])

# REST API v1.1 (旧版但稳定)
REST_API = 'https://api.twitter.com/1.1/statuses/user_timeline.json'

# 或使用 v2
REST_API_V2 = 'https://api.twitter.com/2/users/{user_id}/tweets'


def fetch_rest_api():
    """使用 REST API v1.1"""
    print(f'\n=== REST API v1.1 ===')
    print(f'URL: {REST_API}')
    
    params = {
        'screen_name': 'tutu7gen1',
        'count': 20,
        'exclude_replies': False,
        'tweet_mode': 'extended',
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        'Cookie': COOKIES_STR,
        'Authorization': 'Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGGrjMc',
    }
    
    try:
        resp = requests.get(REST_API, headers=headers, params=params, timeout=15)
        print(f'Status: {resp.status_code}')
        
        if resp.status_code == 200:
            tweets = resp.json()
            print(f'Tweets: {len(tweets)}')
            return tweets
        else:
            print(f'Error: {resp.text[:300]}')
            return []
    except Exception as e:
        print(f'Exception: {e}')
        return []


def fetch_oembed():
    """使用 oembed API 获取单条推文（验证 API 是否可用）"""
    print(f'\n=== oembed API 测试 ===')
    
    # 获取第一条推文的 URL（需要先有推文 ID）
    # 先用用户时间线获取
    tweets = fetch_rest_api()
    
    if tweets:
        for tweet in tweets[:3]:
            tweet_id = tweet.get('id_str', '')
            tweet_url = f'https://twitter.com/tutu7gen1/status/{tweet_id}'
            
            oembed_url = f'https://publish.twitter.com/oembed'
            params = {'url': tweet_url}
            
            resp = requests.get(oembed_url, params=params, timeout=10)
            print(f'oembed for {tweet_id}: Status {resp.status_code}')
            if resp.status_code == 200:
                data = resp.json()
                print(f'  HTML length: {len(data.get("html", ""))}')
                print(f'  Author: {data.get("author_name", "")}')
    
    return tweets


def main():
    tweets = fetch_oembed()
    
    if tweets:
        output = {
            'username': 'tutu7gen1',
            'scraped_at': datetime.now().isoformat(),
            'source': 'rest_api',
            'recent_tweets': [
                {
                    'tweet_id': t.get('id_str'),
                    'text': t.get('full_text', ''),
                    'created_at': t.get('created_at'),
                    'is_retweet': 'retweeted_status' in t,
                    'retweet_count': t.get('retweet_count', 0),
                    'like_count': t.get('favorite_count', 0),
                }
                for t in tweets
            ],
        }
        
        output_path = f'{DATA_DIR}/tutu7gen1_tweets_rest.json'
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        
        print(f'\n数据已保存到 {output_path}')
    else:
        print('获取失败')


if __name__ == '__main__':
    main()
