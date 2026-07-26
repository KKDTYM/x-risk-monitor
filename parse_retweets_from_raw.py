"""
从现有 tweets.json 的 raw 字段解析"已转帖"标记
"""
import json
import re
import os
from datetime import datetime

BASE_DIR = r'F:\Users\Administrator\Documents\WorkBuddy\2026-07-24-21-36-14'
DATA_DIR = os.path.join(BASE_DIR, 'data')

ACCOUNTS = ['dangao0709', 'kaixintangtang']

# 正则：匹配 "用户名 已转帖 被转推用户名 @" 或 "用户名 已转帖 被转推用户名 (描述) @"
RE_RETWEET = re.compile(r'^(.+?)\s+已转帖\s+(.+?)\s+@\w+')
RE_RETWEET_EN = re.compile(r'^(.+?)\s+Reposted\s+(.+?)\s+@\w+')


def parse_retweet(raw_text):
    """从raw文本解析是否为转推"""
    # 匹配中文
    m = RE_RETWEET.match(raw_text.strip())
    if m:
        return {
            'is_retweet': True,
            'account_name': m.group(1),
            'retweet_author_name': m.group(2),
            'type': 'zh_retweet'
        }
    
    # 匹配英文
    m = RE_RETWEET_EN.match(raw_text.strip())
    if m:
        return {
            'is_retweet': True,
            'account_name': m.group(1),
            'retweet_author_name': m.group(2),
            'type': 'en_reposted'
        }
    
    return {'is_retweet': False, 'account_name': '', 'retweet_author_name': '', 'type': ''}


def process_account(username):
    """处理单个账号"""
    print(f"\n{'='*60}")
    print(f"解析 @{username}")
    print(f"{'='*60}")
    
    tweets_path = os.path.join(DATA_DIR, f'{username}_tweets.json')
    if not os.path.exists(tweets_path):
        print(f"  ✗ 未找到 {tweets_path}")
        return None
    
    with open(tweets_path, 'r', encoding='utf-8') as f:
        tweets = json.load(f)
    
    print(f"  ✓ 加载 {len(tweets)} 条推文")
    
    retweet_count = 0
    original_count = 0
    
    for i, tweet in enumerate(tweets):
        raw = tweet.get('raw', '')
        parse_result = parse_retweet(raw)
        
        tweets[i]['is_retweet'] = parse_result['is_retweet']
        tweets[i]['retweet_author_name'] = parse_result['retweet_author_name']
        tweets[i]['retweet_type'] = parse_result['type']
        tweets[i]['account_name'] = parse_result['account_name']
        
        if parse_result['is_retweet']:
            retweet_count += 1
            print(f"  [{i+1}] 转贴: {parse_result['retweet_author_name']}")
        else:
            original_count += 1
    
    print(f"\n  {'='*60}")
    print(f"  @{username} 统计:")
    print(f"  原创: {original_count}")
    print(f"  转贴: {retweet_count}")
    print(f"  总计: {len(tweets)}")
    
    if len(tweets) > 0:
        rt_ratio = retweet_count / len(tweets)
        print(f"  转贴占比: {rt_ratio:.1%}")
        
        if rt_ratio > 0.5:
            print(f"  ⚠️ 转贴占比 >50%，疑似搬运账号")
        elif rt_ratio > 0.8:
            print(f"  ⚠️ 转贴占比 >80%，高疑似矩阵/搬运账号")
    
    output = {
        'username': username,
        'parsed_at': datetime.now().isoformat(),
        'source': 'tweets_json_raw_field_parser',
        'total_count': len(tweets),
        'original_count': original_count,
        'retweet_count': retweet_count,
        'retweet_ratio': retweet_count / len(tweets) if len(tweets) > 0 else 0,
        'tweets': tweets
    }
    
    output_path = os.path.join(DATA_DIR, f'{username}_retweet_parsed.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"  保存: {output_path}")
    
    return output


def main():
    print("X账号转贴解析工具（从raw字段）")
    print(f"目标账号: {', '.join('@' + a for a in ACCOUNTS)}")
    
    results = []
    for account in ACCOUNTS:
        result = process_account(account)
        if result:
            results.append(result)
    
    if results:
        print(f"\n{'='*60}")
        print("所有账号处理完成！")
        print(f"{'='*60}")


if __name__ == '__main__':
    main()
