"""
生成 @muumuujiang 风险评估报告
"""
import json
import os
import datetime
from risk_engine import RiskEngine

PROJECT_DIR = r"F:\Users\Administrator\Documents\WorkBuddy\2026-07-24-21-36-14"
DATA_DIR = os.path.join(PROJECT_DIR, "data")
HANDLE = "muumuujiang"


def gen_report(result, handle, raw_data):
    dims = result.get('dimensions', {})
    tweets = raw_data.get('recent_tweets', [])
    profile = raw_data.get('profile', {})
    
    total = len(tweets)
    retweet_count = sum(1 for t in tweets if t.get('is_retweet'))
    original_count = total - retweet_count
    retweet_ratio = retweet_count / total if total else 0
    
    adult_keywords = ['小穴', '肉棒', '鸡巴', '淫', '精液', '自慰', '高潮', '蜜穴', '屁穴',
        '男娘', '伪娘', '男の娘', 'mtf', 'ftm', '药娘', 'cd', 'crossdress',
        'femboy', 'ts', '乳胶', 'latex', '胶衣', '女仆', '假发', 'cosplay',
        'nsfw', '18+', 'adult', '涩涩', '调教', '拘束', 'sm', '露出',
        '颜射', '足交', '手淫', '飞机杯', '吃药', '事后',
        '援交', '约炮', 'yp', '插穴', '口交', '肛交', '阴道', '阴茎', '阴蒂', '大胸', '巨乳',
        '裸照', '果照', '走光', '姿势', '体位', '操', '干', '婊子', '骚', '操粉', '草粉', '上床']
    
    adult_count = sum(1 for t in tweets if any(kw in str(t.get('text', '')).lower() for kw in adult_keywords))
    
    score = result['score']
    level = result['level']
    
    score_color = '#e74c3c' if score >= 60 else '#f39c12' if score >= 30 else '#2ecc71'
    level_text = '🔴 高风险' if level == 'high' else '🟡 中等风险' if level == 'medium' else '🟢 低风险'
    
    dim_names = {
        'acc_program': '1. ACC 计划合规',
        'acc_marking': '2. ACC 三级标记合规',
        'api_reply': '3. API 自动回复合规',
        'ip_network': '4. IP/网络环境',
        'shadowban': '5. Shadowban 状态',
        'follow_ratio': '6. 关注/粉丝比',
        'premium': '7. Premium 会员等级',
        'content_diversity': '8. 内容多样性',
        'prohibited': '9. 禁止内容零触碰',
    }
    
    bio = profile.get('description', profile.get('bio', ''))
    verified = profile.get('verified', False)
    
    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>@{handle} — X 风险评估 v6</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif; background: #0a0a0a; color: #e0e0e0; padding: 20px; }}
.container {{ max-width: 960px; margin: 0 auto; }}
header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 40px; border-radius: 20px; margin-bottom: 30px; }}
header h1 {{ font-size: 32px; margin-bottom: 8px; }}
header .subtitle {{ opacity: 0.9; font-size: 14px; }}
.profile-info {{ background: #1a1a1a; border-radius: 16px; padding: 24px; margin-bottom: 30px; box-shadow: 0 2px 12px rgba(0,0,0,0.2); }}
.profile-info h3 {{ color: white; margin-bottom: 16px; }}
.profile-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; }}
.profile-item {{ padding: 12px; background: #2a2a2a; border-radius: 8px; }}
.profile-label {{ font-size: 12px; color: #888; }}
.profile-value {{ font-size: 18px; font-weight: bold; color: white; }}
.score-card {{ background: #1a1a1a; border-radius: 20px; padding: 40px; margin-bottom: 30px; text-align: center; box-shadow: 0 4px 20px rgba(0,0,0,0.3); }}
.score-circle {{ width: 180px; height: 180px; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 20px; font-size: 64px; font-weight: bold; color: white; border: 8px solid {score_color}; }}
.level-badge {{ display: inline-block; padding: 12px 32px; border-radius: 24px; font-size: 18px; font-weight: bold; color: white; background: {score_color}; }}
.stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 16px; margin-bottom: 30px; }}
.stat-card {{ background: #1a1a1a; border-radius: 16px; padding: 20px; text-align: center; box-shadow: 0 2px 12px rgba(0,0,0,0.2); }}
.stat-value {{ font-size: 32px; font-weight: bold; color: #667eea; }}
.stat-label {{ font-size: 13px; color: #888; margin-top: 6px; }}
.dimension-card {{ background: #1a1a1a; border-radius: 16px; padding: 24px; margin-bottom: 16px; box-shadow: 0 2px 12px rgba(0,0,0,0.2); }}
.dimension-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; }}
.dimension-name {{ font-weight: bold; font-size: 16px; }}
.dimension-score {{ font-weight: bold; font-size: 22px; color: {score_color}; }}
.dimension-bar {{ height: 10px; background: #333; border-radius: 5px; overflow: hidden; margin-bottom: 14px; }}
.dimension-fill {{ height: 100%; border-radius: 5px; transition: width 0.5s; }}
.issues {{ list-style: none; padding: 0; }}
.issues li {{ padding: 8px 0; font-size: 14px; color: #ccc; border-bottom: 1px solid #2a2a2a; }}
.issues li:last-child {{ border-bottom: none; }}
.recommendation {{ background: #1a1a1a; border-left: 4px solid {score_color}; padding: 20px; border-radius: 0 16px 16px 0; margin-bottom: 30px; }}
.recommendation h3 {{ color: {score_color}; margin-bottom: 10px; }}
footer {{ text-align: center; padding: 30px; color: #555; font-size: 13px; }}
</style>
</head>
<body>
<div class="container">
<header>
<h1>X 账号风险评估 v6</h1>
<div class="subtitle">@{handle} | 基于 X 平台 2026 最新规则 | 9 维度风险评分引擎</div>
</header>

<div class="profile-info">
<h3>账号信息</h3>
<div class="profile-grid">
<div class="profile-item"><div class="profile-label">用户名</div><div class="profile-value">@{handle}</div></div>
<div class="profile-item"><div class="profile-label">昵称</div><div class="profile-value">{profile.get('name', 'N/A')}</div></div>
<div class="profile-item"><div class="profile-label">粉丝数</div><div class="profile-value">{profile.get('followers_count', 0):,}</div></div>
<div class="profile-item"><div class="profile-label">关注数</div><div class="profile-value">{profile.get('following_count', 0):,}</div></div>
<div class="profile-item"><div class="profile-label">认证状态</div><div class="profile-value">{'✅ 已认证' if verified else '❌ 未认证'}</div></div>
<div class="profile-item"><div class="profile-label">Bio</div><div class="profile-value" style="font-size: 14px;">{bio[:50]}...</div></div>
</div>
</div>

<div class="score-card">
<div class="score-circle" style="border-color: {score_color}">
<span style="color: {score_color}">{score}</span>
</div>
<div class="level-badge">{level_text}</div>
</div>

<div class="stats-grid">
<div class="stat-card"><div class="stat-value">{total}</div><div class="stat-label">分析推文数</div></div>
<div class="stat-card"><div class="stat-value">{original_count}</div><div class="stat-label">原创推文</div></div>
<div class="stat-card"><div class="stat-value">{retweet_count}</div><div class="stat-label">转贴推文</div></div>
<div class="stat-card"><div class="stat-value">{retweet_ratio:.0%}</div><div class="stat-label">转贴占比</div></div>
<div class="stat-card"><div class="stat-value">{adult_count}</div><div class="stat-label">成人内容</div></div>
</div>

<h2 style="color: white; margin-bottom: 20px;">📊 9 维度详细评分</h2>
'''
    
    for dim_key in ['acc_program', 'acc_marking', 'api_reply', 'ip_network', 'shadowban', 'follow_ratio', 'premium', 'content_diversity', 'prohibited']:
        dim = dims.get(dim_key, {})
        risk_score = dim.get('risk_score', 0)
        max_risk = dim.get('max_risk', 0)
        issues = dim.get('issues', [])
        
        ratio = risk_score / max_risk if max_risk else 0
        fill_color = '#e74c3c' if ratio > 0.6 else '#f39c12' if ratio > 0.3 else '#2ecc71'
        
        html += f'''<div class="dimension-card">
<div class="dimension-header">
<div class="dimension-name">{dim_names.get(dim_key, dim_key)}</div>
<div class="dimension-score" style="color: {fill_color}">{risk_score} / {max_risk}</div>
</div>
<div class="dimension-bar"><div class="dimension-fill" style="width: {ratio*100:.0f}%; background: {fill_color}"></div></div>
<ul class="issues">
'''
        for issue in issues:
            html += f'<li>{issue}</li>'
        html += '</ul></div>\n'
    
    html += f'''<div class="recommendation">
<h3>💡 评估建议</h3>
<p>{result.get('recommendation', '暂无建议')}</p>
</div>

<footer>
<p>v6 风险评估引擎 | risk_engine.py v4 | 生成时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
</footer>
</div>
</body>
</html>'''
    
    return html


def main():
    # 读取数据
    with open(os.path.join(DATA_DIR, f"{HANDLE}_tweets_syndication.json"), 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    tweets = data.get('recent_tweets', [])
    profile = data.get('profile', {})
    
    profile_data = {
        'username': HANDLE,
        'name': '木木浆',
        'followers_count': profile.get('followers_count', 56594),
        'following_count': profile.get('friends_count', 474),
        'description': profile.get('description', ''),
        'verified': profile.get('verified', False),
    }
    
    account_status = {
        'is_suspended': False, 'is_frozen': False, 'acc_status': 'unknown',
        'premium_type': 'none', 'ip_type': 'unknown', 'search_visibility': True,
        'report_count': 0, 'has_warning': False, 'violation_count': 0,
        'needs_verification': False, 'suspicious_login': False,
        'dirty_device': False, 'shared_ip': False,
    }
    
    raw_data = {
        'recent_tweets': tweets,
        'profile': profile_data,
        'account_status': account_status,
    }
    
    # 评估
    engine = RiskEngine({})
    result = engine.assess_account(raw_data, [])
    
    # 生成报告
    html = gen_report(result, HANDLE, raw_data)
    
    output_path = os.path.join(DATA_DIR, f"{HANDLE}_risk_v6.html")
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"@{HANDLE} 评估完成")
    print(f"总分: {result['score']}, 等级: {result['level']}")
    print(f"报告: {output_path}")


if __name__ == "__main__":
    main()
