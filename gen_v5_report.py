"""
生成v5风险评估HTML报告（含转贴数据）
"""
import json
import os

BASE_DIR = r'F:\Users\Administrator\Documents\WorkBuddy\2026-07-24-21-36-14'
DATA_DIR = os.path.join(BASE_DIR, 'data')


def get_color(level):
    if level == 'high':
        return '#ef4444'
    if level == 'medium':
        return '#f59e0b'
    return '#22c55e'


def level_text(level):
    if level == 'high':
        return '高风险'
    if level == 'medium':
        return '中等风险'
    return '低风险'


def generate_html(accounts):
    html_parts = ['''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>X账号风险评估报告 - 2026-07-26 (v5 含转贴)</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: #f3f4f6;
    color: #111827;
    line-height: 1.6;
    padding: 24px;
}
.container { max-width: 1200px; margin: 0 auto; }
.header {
    background: white; padding: 32px; border-radius: 12px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1); margin-bottom: 32px; text-align: center;
}
.header h1 { font-size: 1.8em; margin-bottom: 8px; }
.header .date { color: #6b7280; font-size: 1em; }
.account-card {
    background: white; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    margin-bottom: 32px; overflow: hidden;
}
.account-header {
    padding: 24px 32px;
    display: flex; align-items: center; justify-content: space-between;
    border-bottom: 1px solid #e5e7eb;
}
.account-handle { font-size: 1.4em; font-weight: 700; }
.account-score {
    font-size: 2em; font-weight: 800;
    display: flex; align-items: baseline; gap: 4px;
}
.account-score .num { font-size: 1.2em; }
.account-score .max { font-size: 0.5em; color: #6b7280; }
.level-badge {
    display: inline-block; padding: 4px 16px; border-radius: 20px;
    color: white; font-weight: 600; font-size: 0.9em;
}
.dimensions-grid {
    display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
    gap: 16px; padding: 24px 32px;
}
.dimension-card {
    border: 1px solid #e5e7eb; border-radius: 8px; padding: 16px;
}
.dimension-title {
    font-weight: 600; margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center;
}
.dimension-score { font-weight: 700; font-size: 1.1em; }
.dimension-bar {
    height: 8px; background: #e5e7eb; border-radius: 4px; margin: 8px 0; overflow: hidden;
}
.dimension-fill {
    height: 100%; border-radius: 4px;
    background: linear-gradient(90deg, #22c55e, #eab308, #ef4444);
}
.dimension-issues { margin-top: 8px; }
.dimension-issues li { margin: 4px 0; font-size: 0.9em; color: #374151; }
.details-section { padding: 0 32px 24px; }
.detail-list { list-style: none; padding: 0; }
.detail-list li { padding: 8px 12px; margin: 4px 0; background: #f9fafb; border-radius: 6px; }
.recommendation {
    margin: 16px 0; padding: 16px; background: #eff6ff; border-radius: 8px; border-left: 4px solid #3b82f6;
}
.retweets-section {
    margin: 16px 32px 24px; padding: 16px; background: #fef3c7; border-radius: 8px; border-left: 4px solid #f59e0b;
}
.retweets-section h3 { margin-bottom: 8px; }
footer { text-align: center; color: #6b7280; padding: 32px; font-size: 0.9em; }
</style>
</head>
<body>
<div class="container">
<div class="header">
<h1>📊 X账号风险评估报告</h1>
<p class="date">v5 · 2026-07-26 · 含转贴数据解析（raw字段“已转帖”标记识别）</p>
</div>
''']
    
    dim_names = {
        'marking': '内容标记合规',
        'prohibited': '禁止内容零触碰',
        'behavior': '行为真实性',
        'environment': '账号环境',
        'report_history': '举报历史',
        'other_compliance': '其他规则合规'
    }
    
    for acc in accounts:
        color = get_color(acc.get('level', 'low'))
        score = acc['score']
        level = acc.get('level', 'low')
        
        html_parts.append(f'''
<div class="account-card">
    <div class="account-header">
        <div>
            <div class="account-handle">{acc.get('handle', '未知账号')}</div>
            <span class="level-badge" style="background: {color}">{level_text(level)}</span>
        </div>
        <div class="account-score" style="color: {color}">
            <span class="num">{score}</span><span class="max">/100</span>
        </div>
    </div>
    
    <div class="dimensions-grid">''')
        
        dims = acc['dimensions']
        for dim_key in ['marking', 'prohibited', 'behavior', 'environment', 'report_history', 'other_compliance']:
            d = dims.get(dim_key, {})
            risk = d.get('risk_score', 0)
            max_r = d.get('max_risk', 0)
            pct = min(risk / max_r * 100, 100) if max_r > 0 else 0
            
            fill_color = '#22c55e' if pct < 40 else '#f59e0b' if pct < 70 else '#ef4444'
            
            html_parts.append(f'''
        <div class="dimension-card">
            <div class="dimension-title">
                <span>{dim_names[dim_key]}</span>
                <span class="dimension-score" style="color: {fill_color}">{risk}/{max_r}</span>
            </div>
            <div class="dimension-bar">
                <div class="dimension-fill" style="width: {pct}%; background: {fill_color}"></div>
            </div>
            <ul class="dimension-issues">''')
            
            for issue in d.get('issues', []):
                html_parts.append(f'<li>{issue}</li>')
            html_parts.append('</ul></div>')
        
        # 转贴统计
        retweet_count = acc.get('retweet_count', 0)
        total_count = acc.get('total_count', 0)
        rt_ratio = acc.get('retweet_ratio', 0)
        
        if retweet_count > 0:
            html_parts.append(f'''
    <div class="retweets-section">
        <h3>📌 转贴统计</h3>
        <p>总推文: {total_count} | 原创: {total_count - retweet_count} | 转贴: {retweet_count} | 占比: {rt_ratio:.1%}</p>
        <p>⚠️ 转贴占比 {rt_ratio:.1%}，{'高疑似搬运号' if rt_ratio > 0.8 else '疑似搬运号' if rt_ratio > 0.5 else '正常'}</p>
    </div>''')
        
        # Details
        html_parts.append('<div class="details-section">')
        html_parts.append('<ul class="detail-list">')
        for detail in acc.get('details', []):
            html_parts.append(f'<li>{detail}</li>')
        html_parts.append('</ul>')
        
        # Recommendation
        html_parts.append(f'<div class="recommendation"><strong>建议：</strong>{acc.get("recommendation", "继续监控")}</div>')
        html_parts.append('</div></div>')
    
    html_parts.append('''
<footer>X 账号风险监控系统 · v5 (2026-07-26) · 含转贴数据解析（raw字段"已转帖"标记识别）</footer>
</div>
</body>
</html>''')
    
    return ''.join(html_parts)


def main():
    accounts = []
    
    for username in ['dangao0709', 'kaixintangtang']:
        json_path = os.path.join(DATA_DIR, f'{username}_risk_v5.json')
        retweet_path = os.path.join(DATA_DIR, f'{username}_retweet_parsed.json')
        
        if not os.path.exists(json_path):
            print(f'✗ {username}: v5 JSON不存在')
            continue
        
        with open(json_path, 'r', encoding='utf-8') as f:
            risk_data = json.load(f)
        
        retweet_data = None
        if os.path.exists(retweet_path):
            with open(retweet_path, 'r', encoding='utf-8') as f:
                retweet_data = json.load(f)
        
        acc = {
            'handle': f'@{username}',
            'score': risk_data['score'],
            'level': risk_data.get('level', 'low'),
            'dimensions': risk_data['dimensions'],
            'details': risk_data.get('details', []),
            'recommendation': risk_data.get('recommendation', '继续监控'),
            'total_count': retweet_data.get('total_count', 0) if retweet_data else 0,
            'retweet_count': retweet_data.get('retweet_count', 0) if retweet_data else 0,
            'retweet_ratio': retweet_data.get('retweet_ratio', 0) if retweet_data else 0,
        }
        
        accounts.append(acc)
    
    if not accounts:
        print('✗ 没有账号数据')
        return
    
    html = generate_html(accounts)
    
    output_path = os.path.join(DATA_DIR, 'dangao0709_and_kaixintangtang_risk_v5.html')
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f'✓ 报告已保存: {output_path}')


if __name__ == '__main__':
    main()
