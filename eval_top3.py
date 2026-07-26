"""对前3高风险账号重新评估+分析为什么没被封"""
import json
import os
import sys
import re

sys.path.insert(0, r'F:\Users\Administrator\Documents\WorkBuddy\2026-07-24-21-36-14')
from risk_engine import RiskEngine

engine = RiskEngine({})

# 按分数排序的前3个
top3 = ['chichi_maddy', 'shutiaoniang', 'jiajia2475']

# 成人内容关键词（更全面）
adult_kws = [
    '小穴', '肉棒', '鸡巴', '淫', '精液', '自慰', '高潮', '蜜穴', '屁穴',
    '男娘', 'femboy', 'ts', '乳胶', '女仆', '假发', 'cosplay', 'spider',
    '金臀', '欲魅', 'Gothic', '蕾丝', '丝袜', '美腿', '玉足', '福利',
    '敏感', '色情', '18+', 'nsfw', 'NSFW', '吃药', '事后',
    '飞机杯', '调教', '主奴', '绿帽', 'ntr', '调教',
    '射精', '高潮', '阴蒂', '阴道', '肛交', '乳交',
    '口交', '颜射', '足交', '手淫', '叫床',
    '药娘', 'cd', 'mtf', 'ftm', '女装', '内裤', '丁字裤',
    '情趣', 'SM', '束缚', '滴蜡', '皮鞭',
    '婊子', '骚', '操', '干', '射',
    '胸部', '屁股', '翘臀', '美臀', '丰臀',
    '奶子', '大胸', '巨乳', '贫乳',
    '果照', '裸照', '露出', '走光',
    '体位', '姿势', '姿势图', '诱惑',
    'yp', '约炮', '一夜情', '援交',
    '交配', '干炮', '草粉',
    '变态', '性欲', '性行为',
]

results = {}

for acc in top3:
    print('=' * 70)
    print(f'账号: @{acc}')
    print('=' * 70)

    tweets_file = f'F:\\Users\\Administrator\\Documents\\WorkBuddy\\2026-07-24-21-36-14\\data\\{acc}_tweets.json'
    raw = json.load(open(tweets_file, encoding='utf-8'))
    tweets = raw.get('recent_tweets', [])
    profile = raw.get('profile', {})

    print(f'推文总数: {len(tweets)}')
    print(f'粉丝: {profile.get("followers_count", "?")}')
    print(f'关注: {profile.get("friends_count", "?")}')
    print(f'注册: {profile.get("created_at", "?")[:10] if profile.get("created_at") else "?"}')

    # 评分
    result = engine.assess_account(
        raw_data={'recent_tweets': tweets, 'profile': profile, 'meta': {'handle': acc}},
        historical_data=[{'data': {'recent_tweets': tweets}}]
    )

    print(f'\n【评分】总分={result["score"]}/100 ({result["level"]})')
    for k, v in result['dimensions'].items():
        if isinstance(v, dict):
            print(f'  {k}: {v.get("risk_score", 0)}/{v.get("max_risk", 1)}')

    # 统计成人内容
    adult_tweets = []
    sensitive_marked = 0
    media_count = 0
    adult_with_media = 0

    for t in tweets:
        if not isinstance(t, dict):
            continue
        text = str(t.get('text', ''))
        text_lower = text.lower()
        is_adult = any(kw.lower() in text_lower for kw in adult_kws)
        has_media = bool(t.get('media')) or bool(t.get('raw') and 'twimg.com' in str(t.get('raw', '')))
        is_sensitive = bool(t.get('is_sensitive') or t.get('possibly_sensitive'))

        if has_media:
            media_count += 1

        if is_adult:
            adult_tweets.append(t)
            if is_sensitive:
                sensitive_marked += 1
            if has_media:
                adult_with_media += 1

    total = len(tweets)
    adult_n = len(adult_tweets)

    print(f'\n【成人内容分析】')
    print(f'  含成人关键词推文: {adult_n}条 ({adult_n/total*100:.1f}%)')
    print(f'  含媒体（图片/视频）推文: {media_count}条 ({media_count/total*100:.1f}%)')
    print(f'  成人+媒体: {adult_with_media}条')
    print(f'  标记Sensitive: {sensitive_marked}条')
    print(f'  未标记: {adult_n - sensitive_marked}条')

    # 时间分布
    dates = []
    for t in tweets:
        if isinstance(t, dict) and t.get('datetime'):
            try:
                dates.append(t['datetime'][:10])
            except:
                pass

    if dates:
        print(f'  时间范围: {min(dates)} ~ {max(dates)}')

    # 显示典型推文
    print(f'\n【5条典型推文样本】')
    for t in tweets[:5]:
        text = str(t.get('text', ''))[:200]
        is_sensitive = bool(t.get('is_sensitive') or t.get('possibly_sensitive'))
        sens_str = '⚠️已标记' if is_sensitive else '  未标记'
        print(f'  [{sens_str}] {text}')

    # X账号合规关键洞察
    print(f'\n【为什么没被封？关键数据】')
    print(f'  1. 已注册 {profile.get("created_at", "?")[:10] if profile.get("created_at") else "?"} - 账号年龄因素')
    print(f'  2. 粉丝/关注比: {profile.get("followers_count", "?")} / {profile.get("friends_count", "?")}')
    print(f'  3. 内容纯文本推文占比: {(total - media_count)/total*100:.1f}%')

    results[acc] = {
        'score': result['score'],
        'level': result['level'],
        'adult_pct': adult_n/total*100 if total else 0,
        'media_pct': media_count/total*100 if total else 0,
        'adult_with_media': adult_with_media,
        'sensitive_marked': sensitive_marked,
        'unmarked': adult_n - sensitive_marked,
        'tweets_total': total,
        'followers': profile.get('followers_count', 0),
        'created_at': profile.get('created_at', '?')
    }
    print()

# 汇总
print('=' * 70)
print('【3账号对比总结】')
print('=' * 70)
print(f'{"账号":<18s} {"评分":>5s} {"等级":>8s} {"成人%":>8s} {"媒体%":>8s} {"未标记":>8s}')
for acc, r in results.items():
    print(f'@{acc:<17s} {r["score"]:>5d} {r["level"]:>8s} {r["adult_pct"]:>7.1f}% {r["media_pct"]:>7.1f}% {r["unmarked"]:>8d}')

# 保存分析结果
output = {
    'accounts': results,
    'analysis_date': '2026-07-26',
    'note': '三个账号均为"男娘/伪娘"主题，发布大量成人向内容，但均未被封禁。'
}
with open('F:\\Users\\Administrator\\Documents\\WorkBuddy\\2026-07-24-21-36-14\\data\\top3_deep_analysis.json', 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)
print(f'\n详细分析已保存: data/top3_deep_analysis.json')