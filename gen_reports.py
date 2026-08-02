#!/usr/bin/env python3
"""生成9个账号的HTML报告"""
import json
import datetime

accounts = ['sunny31059', 'sino11680908', 'shutiaoniang', 'jiajia2475', 'chichi_maddy', 'VulpesM', 'wuuuuuucy', '5277888MCHS', 'urlittlecuteboy']

def get_level_color(level):
    if level == 'high': return '#ef4444'
    if level == 'medium': return '#f59e0b'
    return '#22c55e'

def get_level_text(level):
    if level == 'high': return '高风险'
    if level == 'medium': return '中等风险'
    return '低风险'

html_parts = []
html_parts.append('''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>X账号风险监控报告 - 2026-07-26</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: #f3f4f6;
            color: #111827;
            line-height: 1.6;
            padding: 24px;
        }
        .container { max-width: 1200px; margin: 0 auto; }
        .header {
            background: white;
            padding: 32px;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            margin-bottom: 32px;
            text-align: center;
        }
        .header h1 { font-size: 2em; margin-bottom: 8px; }
        .header .date { color: #6b7280; font-size: 1.1em; }
        .overview-section {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 32px;
        }
        .overview-card {
            background: white;
            padding: 24px;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            border-left: 4px solid #22c55e;
        }
        .overview-card h3 { margin: 0 0 12px 0; font-size: 1.2em; }
        .score-display { font-size: 2.5em; font-weight: bold; }
        .level-badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            margin-top: 8px;
            color: white;
            font-size: 0.9em;
        }
        .detail-section {
            background: white;
            padding: 24px;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            margin-bottom: 24px;
        }
        .detail-section h2 { margin-bottom: 16px; color: #111827; }
        .dimension-row {
            display: flex;
            justify-content: space-between;
            padding: 12px 0;
            border-bottom: 1px solid #f3f4f6;
        }
        .dimension-row:last-child { border-bottom: none; }
        .dimension-name { font-weight: 500; }
        .dimension-score { font-weight: bold; }
        .recommendation {
            padding: 16px;
            border-radius: 8px;
            margin-top: 16px;
            font-weight: 500;
        }
        .recommendation.high { background: #fef2f2; color: #991b1b; }
        .recommendation.medium { background: #fffbeb; color: #92400e; }
        .recommendation.low { background: #f0fdf4; color: #166534; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🛡️ X 账号违规风险监控报告</h1>
            <div class="date">报告日期：2026-07-26（新权重：标记合规40%）</div>
        </div>
''')

all_accounts_html = []

for acc in accounts:
    report_file = f'data/{acc}_risk_v3_new.json'
    try:
        data = json.load(open(report_file, encoding='utf-8'))
    except:
        continue
    
    score = data['score']
    level = data['level']
    meta = data.get('meta', {})
    dims = data.get('dimensions', {})
    details = data.get('details', [])
    recommendation = data.get('recommendation', '')
    
    color = get_level_color(level)
    level_text = get_level_text(level)
    
    # 概览卡片
    overview_card = f'''
    <div class="overview-card" style="border-left-color: {color};">
        <h3>{meta.get('handle', '@' + acc)}</h3>
        <div class="score-display" style="color: {color};">
            {score}/100
        </div>
        <div class="level-badge" style="background: {color};">
            {level_text}
        </div>
        <div style="margin-top: 12px; color: #6b7280; font-size: 0.9em;">
            分析推文: {meta.get('tweets_analyzed', 0)} 条<br>
            粉丝: {meta.get('followers', 'N/A')}
        </div>
    </div>
    '''
    all_accounts_html.append(overview_card)
    
    # 详细维度
    detail_html = f'''
    <div class="detail-section">
        <h2>{meta.get('handle', '@' + acc)} - 详细评分</h2>
        <div style="color: #6b7280; margin-bottom: 16px;">
            分析推文: {meta.get('tweets_analyzed', 0)} 条 | 粉丝: {meta.get('followers', 'N/A')}
        </div>
'''
    
    dim_names = {
        'marking': '内容标记合规',
        'prohibited': '禁止内容零触碰',
        'behavior': '行为真实性',
        'environment': '账号环境',
        'report_history': '举报历史',
        'other_compliance': '其他合规'
    }
    
    for dim_key, dim_name in dim_names.items():
        dim = dims.get(dim_key, {})
        risk_score = dim.get('risk_score', 0)
        max_risk = dim.get('max_risk', 0)
        detail_html += f'''
        <div class="dimension-row">
            <span class="dimension-name">{dim_name}</span>
            <span class="dimension-score" style="color: {'#ef4444' if risk_score > 0 else '#22c55e'};">{risk_score}/{max_risk}</span>
        </div>'''
    
    detail_html += f'''
        <div class="recommendation {level}">
            <strong>建议：</strong>{recommendation}
        </div>
    </div>
'''
    all_accounts_html.append(detail_html)

html_parts.append('        <div class="overview-section">\n' + ''.join(all_accounts_html) + '\n        </div>')

html_parts.append('''
        <div class="detail-section">
            <h2>评分说明</h2>
            <p>新权重（2026-07-26更新）：</p>
            <ul style="margin: 12px 0 12px 24px;">
                <li>内容标记合规（0-40分）：成人内容未标记每条扣4分</li>
                <li>禁止内容零触碰（0-25分）：Tier1违规1条扣20分</li>
                <li>行为真实性（0-15分）：自动化工具信号每种扣5分</li>
                <li>账号环境（0-10分）：新号（粉丝<100）扣3分</li>
                <li>举报历史（0-5分）：举报>5次扣3分</li>
                <li>其他合规（0-5分）：每类违规扣1分</li>
            </ul>
            <p>风险等级：≥60分=高风险，≥30分=中等风险，<30分=低风险</p>
        </div>
    </div>
</body>
</html>''')

full_html = ''.join(html_parts)

with open('data/reports/x_risk_report_2026-07-26_v2.html', 'w', encoding='utf-8') as f:
    f.write(full_html)

print('HTML报告已保存: data/reports/x_risk_report_2026-07-26_v2.html')
print('包含9个账号的评分结果')

# 高风险账号列表
high_risk = []
for acc in accounts:
    report_file = f'data/{acc}_risk_v3_new.json'
    try:
        data = json.load(open(report_file, encoding='utf-8'))
        if data['score'] >= 60:
            high_risk.append(f"@{acc} ({data['score']}分)")
    except:
        pass

if high_risk:
    print(f'\n高风险账号（≥60分）需要发邮件：{", ".join(high_risk)}')
else:
    print('\n无高风险账号需要发邮件')
