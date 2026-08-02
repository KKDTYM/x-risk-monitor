"""
使用 GraphQL API 获取 @tutu7gen1 推文
"""
import json
import time
import requests
from datetime import datetime

PROJECT_DIR = r'F:\Users\Administrator\Documents\WorkBuddy\2026-07-24-21-36-14'
DATA_DIR = f'{PROJECT_DIR}/data'

COOKIES_STR = '; '.join([
    f"auth_token=0555da63fcf228b97af5aec8c8ed4fd6d5841880",
    f"guest_id=v1%3A178505847748990053",
    f"twid=u%3D2081335439026421760",
    f"_twitter_sess=BAh7BiIKZmxhc2hJQzonQWN0aW9uQ29udHJvbGxlcjo6Rmxhc2g6OkZsYXNo%250ASGFzaHsABjoKQHVzZWR7AA%253D%253D--1164b91ac812d853b877e93ddb612b7471bebc74",
    f"auth_multi=\"497862683:443bd09a5c16b0d8e346459f52686dc7be306564|1919756553915428864:a40bfcf10aa9fda18b4e1768fc6d63e567a9e5fc|1969781334114455552:3fe146efd1cc10b8179ef91e36f583d60a5c6e5b\"",
    f"__cf_bm=gC8t1L9RsF3ndSQTlNW44GTP2fH6WB_86U2pvCjlV0U-1785063263.959605-1.0.1.1-D4toXEYknP5RJOyGlG4sM_HGw_2jhgUL6VTmOmum3utpnst26y3miE8TIaLHHRcRuu3qv8JqEVPNwzCXxdysjZc5qHIsdtkUpC0.rWlSzPWSCfviWn93gZVSUwcOiu3D",
    f"ct0=bb33543802aefbd7f6b2496ef8ec78ec578d22decbc0b5a0fa2ff1d66846a7a57deff1cc2b0fbc16f7e3edb3b2bcb9b0758b128c9af16bf0133c44980671ba5f329812ffb971fdd03443edf83423e4ee",
    f"kdt=I26qcLfGtmQPKocgpIA1CmOPLRiS2kYQu8CY2vdA",
    f"personalization_id=\"v1_VF7XpjNa6DEkBMUivBb/xQ==\"",
])

# User ID from previous inspection
USER_ID = '2081335439026421760'

# GraphQL query features (commonly used)
FEATURES = {
    "responsive_web_graphql_timeline_navigation_enabled": True,
    "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
    "responsive_web_graphql_timeline_navigation_enabled": True,
}

QUERY_URL = 'https://x.com/i/api/graphql/bJJiMoaPFmWPMI1a7cXEgT/UserTweetsAndRepliesByUserId'


def fetch_tweets():
    """使用 GraphQL API 获取推文"""
    print(f'请求 URL: {QUERY_URL}')
    print(f'User ID: {USER_ID}')
    
    variables = {
        "userId": USER_ID,
        "count": 100,
        "includePromotedContent": False,
        "withQuickPromoteEligibilityTweetFields": False,
        "withVoice": False,
        "withV2Timeline": True,
    }
    
    features = FEATURES
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Authorization': 'Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGGrjMc',
        'Cookie': COOKIES_STR,
        'X-Twitter-Auth-Type': 'OAuth2Session',
        'X-Twitter-Active-User': 'yes',
        'X-Twitter-Client-Language': 'zh-Hans',
    }
    
    params = {
        'variables': json.dumps(variables),
        'features': json.dumps(features),
    }
    
    try:
        resp = requests.get(QUERY_URL, headers=headers, params=params, timeout=15)
        print(f'Status: {resp.status_code}')
        
        if resp.status_code == 200:
            data = resp.json()
            print(f'Response keys: {data.keys()}')
            
            # 解析推文
            instructions = data.get('data', {}).get('user', {}).get('result', {}).get('timeline', {}).get('timeline', {}).get('instructions', [])
            
            tweets = []
            for instr in instructions:
                if instr.get('type') == 'TimelineAddEntries':
                    for entry in instr.get('entries', []):
                        content = entry.get('content', {})
                        if content.get('entryType') == 'TimelineTimelineItem':
                            item = content.get('itemContent', {})
                            tweet_data = item.get('tweet_result', {}).get('result', {})
                            
                            if tweet_data and tweet_data.get('__typename') == 'Tweet':
                                tweet_id = tweet_data.get('rest_id', '')
                                legacy = tweet_data.get('legacy', {})
                                
                                tweet_info = {
                                    'tweet_id': tweet_id,
                                    'text': legacy.get('full_text', ''),
                                    'created_at': legacy.get('created_at', ''),
                                    'is_retweet': legacy.get('retweeted_status_id', None) is not None,
                                    'retweet_count': legacy.get('retweet_count', 0),
                                    'like_count': legacy.get('favorite_count', 0),
                                    'reply_count': legacy.get('reply_count', 0),
                                    'quote_count': legacy.get('quote_count', 0),
                                }
                                tweets.append(tweet_info)
            
            print(f'解析到 {len(tweets)} 条推文')
            return tweets
        else:
            print(f'Error: {resp.text[:500]}')
            return []
    
    except Exception as e:
        print(f'Exception: {e}')
        return []


def main():
    tweets = fetch_tweets()
    
    output = {
        'username': 'tutu7gen1',
        'scraped_at': datetime.now().isoformat(),
        'source': 'graphql',
        'user_id': USER_ID,
        'recent_tweets': tweets,
    }
    
    output_path = f'{DATA_DIR}/tutu7gen1_tweets_graphql.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f'\n数据已保存到 {output_path}')
    print(f'共 {len(tweets)} 条推文')
    
    # 统计
    retweet_count = sum(1 for t in tweets if t.get('is_retweet'))
    original_count = len(tweets) - retweet_count
    print(f'原创: {original_count}, 转贴: {retweet_count}')
    
    # 显示前 3 条
    print('\n=== 前 3 条推文 ===')
    for i, t in enumerate(tweets[:3], 1):
        print(f'\n{i}. [{t["created_at"]}]')
        print(f'   ID: {t["tweet_id"]}')
        print(f'   文本: {t["text"][:100]}')
        print(f'   转推: {t["is_retweet"]}, 赞: {t["like_count"]}, 回复: {t["reply_count"]}')


if __name__ == '__main__':
    main()
