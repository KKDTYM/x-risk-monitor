#!/usr/bin/env python3
"""批量用旧推文数据重新评分（新权重：标记合规40%）"""
import json
import os
import datetime
import sys

sys.path.insert(0, 'F:\\Users\\Administrator\\Documents\\WorkBuddy\\2026-07-24-21-36-14')
from risk_engine import RiskEngine

accounts = ['sunny31059', 'sino11680908', 'shutiaoniang', 'jiajia2475', 'chichi_maddy', 'VulpesM', 'wuuuuuucy', '5277888MCHS', 'urlittlecuteboy']

# 加载旧格式推文数据（含 recent_tweets 的完整格式）
def load_full_data(acc):
    """返回 (raw_data, profile_info)"""
    # 优先读旧格式（包含完整推文和profile）
    for fname in [f'data/{acc}_tweets.json', f'data/{acc}_tweets_v2.json']:
        if os.path.exists(fname):
            try:
                d = json.load(open(fname, encoding='utf-8'))
                if isinstance(d, dict) and 'recent_tweets' in d:
                    raw_data = {
                        'recent_tweets': d.get('recent_tweets', []),
                        'profile': d.get('profile', {}),
                        'account_status': d.get('account_status', {})
                    }
                    profile_info = {
                        'bio': d.get('profile', {}).get('bio', ''),
                        'followers': d.get('profile', {}).get('followers_count', 0),
                        'following': d.get('profile', {}).get('following_count', 0)
                    }
                    return raw_data, profile_info
            except:
                pass
    return None, {}

engine = RiskEngine({})

print('=' * 90)
print('9个账号重新评分（新权重：标记合规40%，行为真实性15%）')
print('=' * 90)

results = {}
for acc in accounts:
    raw_data, profile = load_full_data(acc)
    
    if raw_data is None or len(raw_data.get('recent_tweets', [])) == 0:
        print(f'@{acc:20s}  无推文数据（跳过）')
        results[acc] = {'score': 0, 'level': 'low'}
        continue
    
    result = engine.assess_account(raw_data, [])
    results[acc] = result
    
    handle = '@' + acc
    score = result['score']
    level = result['level']
    tweet_count = len(raw_data['recent_tweets'])
    
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
            'tweets_analyzed': len(raw_data['recent_tweets']),
            'data_source': 'Re-scored with v3 engine (marking 40%)',
            'scored_at': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        },
        'tweets': raw_data['recent_tweets']
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
