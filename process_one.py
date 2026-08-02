"""
处理单个账号的完整流程：
1. syndication API 抓取推文
2. 跑 risk_engine 评分
3. 生成独立 HTML 报告
"""
import sys
import json
import time
import os
import re
import requests
import importlib
from datetime import datetime

sys.path.insert(0, r'F:\Users\Administrator\Documents\WorkBuddy\2026-07-24-21-36-14')
# 强制重新加载 risk_engine（避免使用缓存版本）
if 'risk_engine' in sys.modules:
    importlib.reload(sys.modules['risk_engine'])
from risk_engine import RiskEngine


def fetch_syndication(username, retries=3):
    """用 syndication API 抓取用户推文（无需cookie）"""
    url = f'https://syndication.twitter.com/srv/timeline-profile/screen-name/{username}'
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

    for attempt in range(retries):
        try:
            resp = requests.get(url, headers=headers, timeout=30)
            if resp.status_code == 200:
                html = resp.text
                tweets_data = []

                # 提取推文ID（用URL中的status/id）
                tweet_ids = re.findall(r'"tweet_id":"(\d+)"', html)

                # 提取文本
                full_texts = re.findall(r'"full_text":"((?:[^"\\]|\\.)*)"', html)

                # 提取日期
                created_ats = re.findall(r'"created_at":"([^"]+)"', html)

                # 提取screen_name
                screen_names = re.findall(r'"screen_name":"([^"]+)"', html)

                # 提取possibly_sensitive
                sensitivities = re.findall(r'"possibly_sensitive":(true|false)', html)

                # 提取media_url
                media_urls = re.findall(r'"media_url":"([^"]+)"', html)

                for i, text in enumerate(full_texts):
                    # syndication API 的文本是双重编码：原始 utf-8 被当成 latin1 字符串
                    try:
                        decoded = text.encode('latin1').decode('utf-8')
                    except:
                        decoded = text
                    decoded = decoded.replace('\\n', '\n').replace('\\t', ' ').replace('\\/', '/')

                    has_media = bool(media_urls[i]) if i < len(media_urls) else False
                    # 推文中包含 t.co 短链接也算媒体（syndication 不返回media_url，但有图片推文都会有 t.co 链接）
                    has_tco_link = 'https://t.co/' in decoded

                    # 检测 retweet（X 标准格式是 "RT @xxx" 开头）
                    is_retweet = decoded.lstrip().startswith('RT @')
                    # 提取原作者（如果RT）
                    rt_author = ''
                    if is_retweet:
                        # 提取 RT @username 中的用户名
                        import re as _re
                        m = _re.match(r'RT\s+@([A-Za-z0-9_]+)', decoded)
                        if m:
                            rt_author = m.group(1)

                    tweets_data.append({
                        'text': decoded,
                        'tweet_id': tweet_ids[i] if i < len(tweet_ids) else '',
                        'datetime': created_ats[i] if i < len(created_ats) else '',
                        'is_sensitive': sensitivities[i] == 'true' if i < len(sensitivities) else False,
                        'has_image': has_media or has_tco_link,
                        'is_retweet': is_retweet,
                        'retweet_author': rt_author,
                        'likes': 0,
                        'retweets': 0,
                        'original_author': screen_names[0] if screen_names else username,
                        'raw': decoded
                    })

                return tweets_data
            elif resp.status_code == 429:
                wait = 10 * (attempt + 1)
                print(f'  限流，等待 {wait}s...')
                time.sleep(wait)
            else:
                print(f'  HTTP {resp.status_code}')
                return []
        except Exception as e:
            print(f'  错误: {e}')
            time.sleep(5)

    return []


def fetch_user_profile(username):
    """用 Fxtwitter API 获取用户信息"""
    url = f'https://api.fxtwitter.com/{username}'
    try:
        resp = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            user = data.get('user', {})
            return {
                'name': user.get('name', ''),
                'description': user.get('description', ''),
                'followers_count': user.get('followers', 0),
                'friends_count': user.get('following', 0),
                'statuses_count': user.get('tweets', 0),
                'media_count': user.get('media_count', 0),
                'created_at': user.get('joined', ''),
                'verified': user.get('verification', {}).get('verified', False),
                'avatar_url': user.get('avatar_url', ''),
                'protected': user.get('protected', False)
            }
    except Exception as e:
        print(f'  Profile错误: {e}')
    return {}


def save_tweets(username, tweets, profile):
    """保存为引擎需要的格式"""
    data = {
        'username': username,
        'scraped_at': datetime.now().isoformat(),
        'source': 'syndication_api',
        'profile': profile,
        'recent_tweets': tweets
    }
    fname = f'F:\\Users\\Administrator\\Documents\\WorkBuddy\\2026-07-24-21-36-14\\data\\{username}_tweets_syndication.json'
    with open(fname, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return fname


def score_account(username, tweets, profile):
    """评分"""
    engine = RiskEngine({})
    result = engine.assess_account(
        raw_data={'recent_tweets': tweets, 'profile': profile, 'meta': {'handle': username}},
        historical_data=[{'data': {'recent_tweets': tweets}}]
    )
    result['meta'] = {
        'handle': f'@{username}',
        'name': profile.get('name', username),
        'bio': profile.get('description', '')[:200],
        'followers': profile.get('followers_count', '?'),
        'following': profile.get('friends_count', '?'),
        'tweets_analyzed': len(tweets),
        'data_source': 'X Syndication API (2026-07-26)',
        'scored_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    # 保存评分
    out_file = f'F:\\Users\\Administrator\\Documents\\WorkBuddy\\2026-07-24-21-36-14\\data\\{username}_risk_final.json'
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    return result


def render_html(username, result):
    """生成独立HTML报告"""
    meta = result.get('meta', {})
    score = result['score']
    level = result['level']
    dims = result['dimensions']
    details = result['details']
    recommendation = result['recommendation']

    dim_names = {
        'marking': '内容标记合规',
        'prohibited': '禁止内容',
        'behavior': '行为真实性',
        'environment': '账号环境',
        'report_history': '举报历史',
        'other_compliance': '其他合规'
    }

    level_info = {
        'high': ('#ef4444', '#fee2e2', '🔴 高风险'),
        'medium': ('#f59e0b', '#fef3c7', '🟡 中等风险'),
        'low': ('#22c55e', '#dcfce7', '🟢 低风险')
    }
    color, bg_color, level_text = level_info.get(level, ('#6b7280', '#f3f4f6', '⚪ 未知'))

    # 渲染维度
    dim_html = ''
    for dim_key, dim_data in dims.items():
        if not isinstance(dim_data, dict):
            continue
        risk = dim_data.get('risk_score', 0)
        max_risk = dim_data.get('max_risk', 1)
        pct = (risk / max_risk * 100) if max_risk > 0 else 0

        dim_cn = dim_names.get(dim_key, dim_key)
        issues = dim_data.get('issues', [])

        bar_color = '#ef4444' if pct >= 80 else '#f59e0b' if pct >= 40 else '#22c55e'

        issues_html = ''
        if issues:
            issues_html = '<ul style="list-style: none; padding: 4px 0 0 0; font-size: 0.85em;">'
            for issue in issues:
                if '⚠️' in str(issue):
                    issues_html += f'<li style="color: #dc2626; padding: 2px 0;">• {issue}</li>'
                elif '✅' in str(issue):
                    issues_html += f'<li style="color: #16a34a; padding: 2px 0;">• {issue}</li>'
                else:
                    issues_html += f'<li style="color: #6b7280; padding: 2px 0;">• {issue}</li>'
            issues_html += '</ul>'

        dim_html += f'''<div style="margin-bottom: 16px; padding: 12px; background: #f9fafb; border-radius: 8px;">
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
<strong style="color: #1f2937;">{dim_cn}</strong>
<span style="color: {bar_color}; font-weight: bold;">{risk}/{max_risk}</span>
</div>
<div style="background: #e5e7eb; height: 10px; border-radius: 5px; overflow: hidden;">
<div style="height: 100%; width: {pct:.1f}%; background: {bar_color};"></div>
</div>
{issues_html}
</div>'''

    detail_html = ''
    for d in details:
        if '⚠️' in str(d):
            detail_html += f'<li style="padding: 6px 0; color: #dc2626;">⚠️ {d}</li>'
        elif '✅' in str(d):
            detail_html += f'<li style="padding: 6px 0; color: #16a34a;">✅ {d}</li>'
        else:
            detail_html += f'<li style="padding: 6px 0; color: #4b5563;">• {d}</li>'

    bio = meta.get('bio', '') or '无'
    today = datetime.now().strftime('%Y-%m-%d %H:%M')

    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>X账号风险评估 - {meta.get('handle', '@' + username)}</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif; background: #f3f4f6; color: #111827; line-height: 1.6; padding: 24px; }}
.container {{ max-width: 900px; margin: 0 auto; }}
.header {{ background: linear-gradient(135deg, #1e40af 0%, #3b82f6 100%); color: white; padding: 32px; border-radius: 12px; text-align: center; margin-bottom: 24px; }}
.header h1 {{ font-size: 1.6em; margin-bottom: 8px; }}
.header .date {{ font-size: 0.95em; opacity: 0.9; }}
.score-card {{ background: white; padding: 32px; border-radius: 12px; margin-bottom: 24px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); text-align: center; }}
.score-big {{ font-size: 4em; font-weight: bold; color: {color}; line-height: 1; }}
.score-label {{ display: inline-block; margin-top: 12px; padding: 8px 24px; background: {bg_color}; color: {color}; border-radius: 20px; font-size: 1.1em; font-weight: bold; }}
.meta-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; margin: 24px 0; }}
.meta-card {{ padding: 14px; background: #f9fafb; border-radius: 8px; text-align: center; }}
.meta-card .label {{ font-size: 0.85em; color: #6b7280; margin-bottom: 4px; }}
.meta-card .value {{ font-size: 1.3em; font-weight: bold; color: #111827; }}
.bio {{ background: white; padding: 16px 24px; border-radius: 12px; margin-bottom: 24px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); }}
.bio-label {{ font-size: 0.85em; color: #6b7280; margin-bottom: 6px; }}
.bio-text {{ color: #4b5563; font-size: 0.95em; }}
.section {{ background: white; padding: 24px; border-radius: 12px; margin-bottom: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); }}
.section h2 {{ margin-bottom: 16px; color: #1f2937; font-size: 1.2em; }}
.detail-list {{ list-style: none; padding: 0; }}
.rec-box {{ margin-top: 16px; padding: 16px; border-radius: 8px; background: #f0f9ff; border-left: 4px solid #3b82f6; color: #1e40af; }}
.footer {{ text-align: center; padding: 24px; color: #9ca3af; font-size: 0.85em; }}
</style>
</head>
<body>
<div class="container">
<div class="header">
<h1>📊 X账号风险评估报告</h1>
<div class="date">{today} | {meta.get('handle', '@' + username)}</div>
</div>

<div class="score-card">
<div class="score-big">{score}/100</div>
<div class="score-label">{level_text}</div>
<div class="meta-grid">
<div class="meta-card"><div class="label">推文分析</div><div class="value">{meta.get('tweets_analyzed', '?')}</div></div>
<div class="meta-card"><div class="label">粉丝数</div><div class="value">{meta.get('followers', '?')}</div></div>
<div class="meta-card"><div class="label">关注数</div><div class="value">{meta.get('following', '?')}</div></div>
</div>
</div>

<div class="bio">
<div class="bio-label">📝 账号简介</div>
<div class="bio-text">{bio}</div>
</div>

<div class="section">
<h2>📋 6维度风险评分</h2>
{dim_html}
</div>

<div class="section">
<h2>🔍 风险详情</h2>
<ul class="detail-list">
{detail_html}
</ul>
</div>

<div class="section">
<h2>💡 处置建议</h2>
<div class="rec-box">
{recommendation}
</div>
</div>

<div class="footer">
报告由 X 账号风险监控系统 v3 自动生成<br>
评分权重: 内容标记合规40% + 禁止内容25% + 行为真实性15% + 账号环境10% + 举报历史5% + 其他合规5%
</div>
</div>
</body>
</html>'''


def process_account(username, use_existing=False):
    """处理单个账号的完整流程"""
    print(f'\n{"=" * 60}')
    print(f'账号: @{username}')
    print(f'{"=" * 60}')

    # 1. 抓取推文（或用已有数据）
    existing_tweets_file = f'F:\\Users\\Administrator\\Documents\\WorkBuddy\\2026-07-24-21-36-14\\data\\{username}_tweets_syndication.json'

    if use_existing and os.path.exists(existing_tweets_file):
        print(f'1. 使用已有数据...')
        with open(existing_tweets_file, encoding='utf-8') as f:
            data = json.load(f)
        tweets = data.get('recent_tweets', [])
        profile = data.get('profile', {})
        print(f'   推文: {len(tweets)}条（已有数据）')
    else:
        print(f'1. 抓取推文...')
        tweets = fetch_syndication(username)
        print(f'   获取 {len(tweets)} 条推文')

        if not tweets:
            print(f'   ⚠️ 未获取到推文')
            return None

        # 2. 获取profile
        print(f'2. 获取账号信息...')
        profile = fetch_user_profile(username)
        if profile:
            print(f'   粉丝: {profile.get("followers_count", "?")}, 关注: {profile.get("friends_count", "?")}')
            print(f'   简介: {profile.get("description", "")[:100]}')

        # 3. 保存数据
        save_tweets(username, tweets, profile)

    # 4. 评分
    print(f'3. 评分...')
    result = score_account(username, tweets, profile)
    print(f'   评分: {result["score"]}/100 ({result["level"]})')

    # 5. 生成HTML
    print(f'4. 生成HTML报告...')
    html = render_html(username, result)
    out_file = f'F:\\Users\\Administrator\\Documents\\WorkBuddy\\2026-07-24-21-36-14\\data\\reports\\x_risk_{username}_2026-07-26.html'
    with open(out_file, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'   报告: {out_file}')

    return {
        'username': username,
        'tweets': len(tweets),
        'score': result['score'],
        'level': result['level'],
        'report': out_file
    }


if __name__ == '__main__':
    username = sys.argv[1]
    use_existing = '--use-existing' in sys.argv
    result = process_account(username, use_existing=use_existing)
    if result:
        print(f'\n✓ @{username} 完成')
        print(f'  推文: {result["tweets"]}, 评分: {result["score"]}, 等级: {result["level"]}')
    else:
        print(f'\n✗ @{username} 失败')