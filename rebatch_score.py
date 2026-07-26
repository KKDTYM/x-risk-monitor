#!/usr/bin/env python3
"""批量用旧推文数据重新评分（新权重：标记合规40%）"""
import json
import os
import datetime
import sys

sys.path.insert(0, 'F:\\Users\\Administrator\\Documents\\WorkBuddy\\2026-07-24-21-36-14')
from risk_engine import RiskEngine

accounts = ['sunny31059', 'sino11680908', 'shutiaoniang', 'jiajia2475', 'chichi_maddy', 'VulpesM', 'wuuuuuucy', '5277888MCHS', 'urlittlecuteboy']

# 加载新推文数据（如果有更新的）
def load_tweets(acc):
    # 优先读新数据
    for fname in [f'data/{acc}_tweets_new.json', f'data/{acc}_timeline.json', f'data/{acc}_tweets.json']:
        if os.path.exists(fname):
            try:
                d = json.load(open(fname, encoding='utf-8'))
                if isinstance(d, list):
                    return d
                if isinstance(d, dict) and 'tweets' in d:
                    return d['tweets']
            except:
                pass
    return []

# 加载旧风险报告中的 profile 信息
def load_profile(acc):
    risk_file = f'data/{acc}_risk_v3.json'
    if os.path.exists(risk_file):
        try:
            d = json.load(open(risk_file, encoding='utf-8'))
            return d.get('meta', {})
        except:
            pass
    return {}

engine = RiskEngine({})

print('=' * 90)
print('9个账号重新评分（新权重：标记合规40%）')
print('=' * 90)

results = {}
for acc in accounts:
    tweets = load_tweets(acc)
    profile = load_profile(acc)
    
    raw_data = {
        'recent_tweets': tweets,
        'profile': profile,
        'account_status': {}
    }
    
    result = engine.assess_account(raw_data, [])
    results[acc] = result
    
    handle = '@' + acc
    score = result['score']
    level = result['level']
    tweet_count = len(tweets)
    
    print(f'{handle:20s}  分数={str(score):>3s}/100  等级={level:10s}  分析推文={tweet_count}')
    
    # 保存新风险报告
    new_report = {
        'score': score,
        'level': level,
        'details': result['details'],
        'recommendation': result['recommendation'],
        'dimensions': result['dimensions'],
        'meta': {
            'handle': '@' + acc,
            'name': acc,
            'bio': profile.get('bio', ''),
            'followers': profile.get('followers', 0),
            'following': profile.get('following', 0),
            'tweets_analyzed': len(tweets),
            'data_source': 'Re-scored with v3 engine (marking 40%)',
            'scored_at': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        },
        'tweets': [t for t in tweets if isinstance(t, dict)]
    }
    
    with open(f'data/{acc}_risk_v3_new.json', 'w', encoding='utf-8') as f:
        json.dump(new_report, f, ensure_ascii=False, indent=2)

print('=' * 90)
print('新报告已保存到 data/*_risk_v3_new.json')
print('=' * 90)

# 检查是否需要发邮件（≥60分）
high_risk = [acc for acc, r in results.items() if r['score'] >= 60]
if high_risk:
    print(f'\n需要发邮件的高风险账号：{", ".join("@" + a for a in high_risk)}')
else:
    print('\n无高风险账号（≥60分）需要发邮件')
