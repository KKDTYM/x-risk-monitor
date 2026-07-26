"""
使用 Syndication API 抓取 @tutu7gen1 的推文数据
"""
import json
import os
import re
import requests
from datetime import datetime

PROJECT_DIR = r"F:\Users\Administrator\Documents\WorkBuddy\2026-07-24-21-36-14"
DATA_DIR = os.path.join(PROJECT_DIR, "data")

def fetch_with_syndication_api(username):
    """通过 Syndication API 获取推文"""
    url = f"https://syndication.twitter.com/srv/timeline/profile/{username}"
    
    params = {
        'dpr': '1',
        'features': 'TFW.timeline:nullify_pgpe_tweet_offset,TFW.left_nav:HEALTH_CHECK_TREATMENT,TFW_tweet_insert_model_order_merging:true,TFWUseFlowBebopSelector:false,TFWApiOverrides:true,TFW.timeline:interpolate_api_offset,TFWDebouncePaginate:true,TFWAddSuggestionsToProfileTimeline:true',
        'lang': 'zh-cn',
        'queryIdentifier': 'TntNqCC0TpM0Yd6TapuMgQ==',
        'count': 40,
        'include_promote_content': 'true',
        'include_ext_sensitive_media_warning': 'true',
        'client_version': '2c39ee5_f7ae0aea62096f7c33a223c3b3565a4bf78455a0e40d125e29463035139',
        'withReactions': 'true',
        'withSuperFollowsTimeline': 'true',
        'withSuperFollowsTweet': 'true',
        'withReply': 'true',
        'withVanityUsername': 'true',
        'withVoice': 'true',
        'withSuperFollowsUser': 'true',
        'supportAllBuyers': 'true',
        'withClientLanguage': 'true',
        'withTokenizeChirperResultsV2': 'true',
    }
    
    headers = {
        'Accept': '*/*',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'Authorization': 'Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1ZV7lfngF52A2IzXymN3qm9chm4U%2FcWpStLkQ%3DdZQ9T',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
    }
    
    resp = requests.get(url, params=params, headers=headers, timeout=30)
    
    if resp.status_code == 200:
        return resp.json()
    else:
        print(f"API Error: {resp.status_code}")
        print(resp.text[:500])
        return None


def parse_timeline_response(data):
    """解析 Syndication API 响应，提取推文"""
    if not data:
        return []
    
    tweets = []
    
    def extract_tweets(obj):
        results = []
        if not isinstance(obj, dict):
            return results
        
        # 路径 1: data.timeline.instructions[*].entries[*].content.itemContent
        if 'timeline' in obj and isinstance(obj['timeline'], dict):
            timeline = obj['timeline']
            if 'instructions' in timeline:
                for inst in timeline['instructions']:
                    if 'entries' in inst:
                        for entry in inst['entries']:
                            content = entry.get('content', {})
                            if content.get('entryType') == 'TimelineTimelineItem':
                                item = content.get('itemContent', {})
                                if item:
                                    results.append(item)
        
        # 路径 2: 直接找 tweet_results
        if 'globalObjects' in obj:
            global_objs = obj['globalObjects']
            if 'tweets' in global_objs:
                for tweet_id, tweet_data in global_objs['tweets'].items():
                    if tweet_data:
                        tweet_data['tweet_id'] = tweet_id
                        results.append(tweet_data)
        
        return results
    
    tweets = extract_tweets(data)
    return tweets


def format_tweets(raw_tweets):
    """格式化推文数据为统一格式"""
    formatted = []
    
    for raw in raw_tweets:
        tweet = {
            'tweet_id': raw.get('id', raw.get('tweet_id', '')),
            'text': '',
            'datetime': raw.get('created_at', ''),
            'is_sensitive': raw.get('possibly_sensitive', False),
            'has_image': False,
            'is_retweet': raw.get('retweeted', False),
            'retweet_author': '',
            'likes': 0,
            'retweets': 0,
            'replies': 0,
            'views': 0,
        }
        
        # 提取文本
        if 'text' in raw:
            tweet['text'] = raw['text']
        
        # 检查是否有媒体
        if 'entities' in raw and 'media' in raw['entities']:
            media_list = raw['entities']['media']
            if media_list:
                tweet['has_image'] = any(m.get('type') == 'photo' for m in media_list)
        
        # 提取互动数据（从 legacy 字段）
        legacy = raw.get('legacy', {})
        if legacy:
            tweet['likes'] = legacy.get('favorite_count', 0)
            tweet['retweets'] = legacy.get('retweet_count', 0)
            tweet['replies'] = legacy.get('reply_count', 0)
            tweet['views'] = legacy.get('impression_count', 0)
        
        formatted.append(tweet)
    
    return formatted


def main():
    username = "tutu7gen1"
    
    print(f"抓取 @{username} 数据...")
    
    # 获取原始数据
    data = fetch_with_syndication_api(username)
    if not data:
        print("抓取失败")
        return
    
    # 保存原始响应
    with open(os.path.join(DATA_DIR, f"{username}_syndication_raw.json"), 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print("原始响应已保存")
    
    # 解析推文
    raw_tweets = parse_timeline_response(data)
    print(f"解析到 {len(raw_tweets)} 条推文")
    
    if not raw_tweets:
        print("未解析到推文，保存空数据")
        result = {
            'username': username,
            'scraped_at': datetime.now().isoformat(),
            'source': 'syndication_api',
            'profile': {},
            'recent_tweets': [],
        }
    else:
        tweets = format_tweets(raw_tweets)
        
        # 获取 profile
        profile = {
            'username': username,
        }
        
        # 尝试从响应中提取 profile
        if 'globalObjects' in data and 'users' in data['globalObjects']:
            user_data = data['globalObjects']['users'].get(username, {})
            if user_data:
                profile['name'] = user_data.get('name', '')
                profile['bio'] = user_data.get('description', '')
                profile['followers_count'] = user_data.get('followers_count', 0)
                profile['following_count'] = user_data.get('friends_count', 0)
                profile['verified'] = user_data.get('verified', False)
        
        # 组装数据
        result = {
            'username': username,
            'scraped_at': datetime.now().isoformat(),
            'source': 'syndication_api',
            'profile': profile,
            'recent_tweets': tweets[:40],  # 最多 40 条
        }
    
    # 保存
    output_path = os.path.join(DATA_DIR, f"{username}_tweets_syndication.json")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"数据已保存到 {output_path}")
    
    # 统计
    if result.get('recent_tweets'):
        retweet_count = sum(1 for t in result['recent_tweets'] if t.get('is_retweet'))
        with_likes = sum(1 for t in result['recent_tweets'] if t.get('likes', 0) > 0)
        print(f"总计 {len(result['recent_tweets'])} 条 | 转贴 {retweet_count} | 有互动 {with_likes}")


if __name__ == "__main__":
    main()
