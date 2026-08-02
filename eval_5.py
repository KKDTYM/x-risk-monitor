"""
用现有数据评估5个数据完整的账号
不重新抓取，只跑评分引擎
"""
import json
import os
import sys

sys.path.insert(0, r'F:\Users\Administrator\Documents\WorkBuddy\2026-07-24-21-36-14')
from risk_engine import RiskEngine

# 5个数据完整的账号
accounts = ['shutiaoniang', 'chichi_maddy', 'jiajia2475', 'sino11680908', 'VulpesM']

# 初始化引擎
engine = RiskEngine({})

results = {}

for acc in accounts:
    print(f'\n{"=" * 70}')
    print(f'账号: @{acc}')
    print(f'{"=" * 70}')

    tweets_file = f'F:\\Users\\Administrator\\Documents\\WorkBuddy\\2026-07-24-21-36-14\\data\\{acc}_tweets.json'

    if not os.path.exists(tweets_file):
        print(f'  ✗ 无推文数据文件')
        continue

    with open(tweets_file, encoding='utf-8') as f:
        raw_data = json.load(f)

    # 标准化格式：把 tweets 和 profile 提取出来
    if 'recent_tweets' in raw_data:
        tweets = raw_data['recent_tweets']
        profile = raw_data.get('profile', {})
    elif 'tweets' in raw_data:
        tweets = raw_data['tweets']
        profile = raw_data.get('profile', {})
    else:
        tweets = raw_data if isinstance(raw_data, list) else []
        profile = {}

    print(f'  推文数: {len(tweets)}')
    print(f'  粉丝: {profile.get("followers_count", "?")}')
    print(f'  关注: {profile.get("friends_count", "?")}')

    # 评分
    try:
        result = engine.assess_account(
            raw_data={"recent_tweets": tweets, "profile": profile, "meta": {"handle": acc}},
            historical_data=[{"data": {"recent_tweets": tweets}}]
        )

        # 添加元数据
        result['meta'] = {
            'handle': f'@{acc}',
            'name': profile.get('name', acc),
            'bio': profile.get('description', '')[:100],
            'followers': profile.get('followers_count', '?'),
            'following': profile.get('friends_count', '?'),
            'tweets_analyzed': len(tweets),
            'data_source': 'Existing Data (Playwright Cookie-Authorized)',
            'scored_at': '2026-07-26 13:55'
        }

        score = result['score']
        level = result['level']
        dims = result['dimensions']

        print(f'\n  ★ 评分: {score}/100 ({level}风险)')
        print(f'  ★ 维度细分:')
        for dim_name, dim_data in dims.items():
            if isinstance(dim_data, dict):
                max_risk = dim_data.get('max_risk', '?')
                risk = dim_data.get('risk_score', 0)
                print(f'    - {dim_name}: {risk}/{max_risk} 分')

        print(f'\n  风险详情:')
        for d in result['details']:
            print(f'    • {d}')

        print(f'\n  建议: {result["recommendation"]}')

        results[acc] = result

        # 保存
        out_file = f'F:\\Users\\Administrator\\Documents\\WorkBuddy\\2026-07-24-21-36-14\\data\\{acc}_risk_final.json'
        with open(out_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

    except Exception as e:
        print(f'  ✗ 评分错误: {e}')
        import traceback
        traceback.print_exc()

# 汇总
print('\n' + '=' * 70)
print('5个账号评分汇总')
print('=' * 70)
print(f"{'账号':<20s} {'分数':>6s} {'等级':>8s} {'推文数':>8s}")
print('-' * 70)
for acc, r in results.items():
    score = r['score']
    level = r['level']
    tweets = r['meta']['tweets_analyzed']
    print(f'@{acc:<19s} {score:>6d} {level:>8s} {tweets:>8d}')