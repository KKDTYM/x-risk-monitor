"""
为5个数据完整的账号生成简洁的HTML评估报告
"""
import json
import os
from datetime import datetime

accounts = ['shutiaoniang', 'chichi_maddy', 'jiajia2475', 'sino11680908', 'VulpesM']

# 维度名称（中文）
dim_names = {
    'marking': '内容标记合规',
    'prohibited': '禁止内容',
    'behavior': '行为真实性',
    'environment': '账号环境',
    'report_history': '举报历史',
    'other_compliance': '其他合规'
}

# 风险等级配色
level_colors = {
    'high': ('#ef4444', '#fee2e2', '🔴'),
    'medium': ('#f59e0b', '#fef3c7', '🟡'),
    'low': ('#22c55e', '#dcfce7', '🟢')
}

HTML_HEAD = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>X账号风险评估报告 - 5个账号</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif; background: #f3f4f6; color: #111827; line-height: 1.6; padding: 24px; }
.container { max-width: 1100px; margin: 0 auto; }
.header { background: linear-gradient(135deg, #1e40af 0%, #3b82f6 100%); color: white; padding: 32px; border-radius: 12px; text-align: center; margin-bottom: 24px; }
.header h1 { font-size: 1.8em; margin-bottom: 8px; }
.header .date { font-size: 0.95em; opacity: 0.9; }
.summary { background: white; padding: 24px; border-radius: 12px; margin-bottom: 24px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); }
.summary table { width: 100%; border-collapse: collapse; }
.summary th, .summary td { padding: 12px; text-align: left; border-bottom: 1px solid #e5e7eb; }
.summary th { background: #f9fafb; font-weight: 600; }
.account-card { background: white; padding: 24px; border-radius: 12px; margin-bottom: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); }
.account-header { display: flex; align-items: center; gap: 16px; margin-bottom: 20px; padding-bottom: 16px; border-bottom: 2px solid #e5e7eb; }
.handle { font-size: 1.5em; font-weight: bold; color: #1f2937; }
.score-box { display: inline-block; padding: 8px 20px; border-radius: 20px; font-size: 1.3em; font-weight: bold; }
.dim-row { display: grid; grid-template-columns: 1fr 2fr; gap: 12px; padding: 10px; border-bottom: 1px solid #f3f4f6; }
.dim-name { color: #4b5563; font-weight: 500; }
.bar-container { background: #e5e7eb; height: 8px; border-radius: 4px; overflow: hidden; }
.bar-fill { height: 100%; transition: width 0.3s; }
.detail-list { list-style: none; padding: 12px 0; }
.detail-list li { padding: 6px 0; color: #4b5563; }
.detail-list li.warning { color: #dc2626; }
.detail-list li.ok { color: #16a34a; }
.rec-box { margin-top: 16px; padding: 14px; border-radius: 8px; background: #f0f9ff; border-left: 4px solid #3b82f6; }
.meta-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; margin-bottom: 16px; }
.meta-card { padding: 10px; background: #f9fafb; border-radius: 6px; }
.meta-card .label { font-size: 0.8em; color: #6b7280; }
.meta-card .value { font-size: 1.1em; font-weight: bold; color: #111827; }
.footer { text-align: center; padding: 24px; color: #9ca3af; font-size: 0.85em; }
</style>
</head>
<body>
<div class="container">
<div class="header">
<h1>📊 X账号风险监控报告</h1>
<div class="date">评估日期: __DATE__ | 数据完整的5个账号</div>
</div>
'''

def render_account(acc, result):
    meta = result.get('meta', {})
    score = result['score']
    level = result['level']
    dims = result['dimensions']
    details = result['details']
    recommendation = result['recommendation']

    color, bg_color, icon = level_colors.get(level, ('#6b7280', '#f3f4f6', '⚪'))

    # 渲染维度
    dim_html = ''
    for dim_key, dim_data in dims.items():
        if not isinstance(dim_data, dict):
            continue
        risk = dim_data.get('risk_score', 0)
        max_risk = dim_data.get('max_risk', 1)
        pct = (risk / max_risk * 100) if max_risk > 0 else 0

        dim_cn = dim_names.get(dim_key, dim_key)

        # 颜色按风险比例
        if pct >= 80:
            bar_color = '#ef4444'
        elif pct >= 40:
            bar_color = '#f59e0b'
        else:
            bar_color = '#22c55e'

        dim_html += f'''
        <div class="dim-row">
            <div class="dim-name">{dim_cn} ({risk}/{max_risk})</div>
            <div>
                <div class="bar-container">
                    <div class="bar-fill" style="width: {pct:.1f}%; background: {bar_color};"></div>
                </div>
            </div>
        </div>'''

    # 渲染详情列表
    detail_html = ''
    for d in details:
        if '⚠️' in d:
            detail_html += f'<li class="warning">• {d}</li>'
        elif '✅' in d:
            detail_html += f'<li class="ok">• {d}</li>'
        else:
            detail_html += f'<li>• {d}</li>'

    return f'''
    <div class="account-card">
        <div class="account-header">
            <div class="handle">{meta.get('handle', '@' + acc)}</div>
            <div class="score-box" style="background: {bg_color}; color: {color};">
                {icon} {score}/100 ({level}风险)
            </div>
        </div>

        <div class="meta-grid">
            <div class="meta-card">
                <div class="label">粉丝数</div>
                <div class="value">{meta.get('followers', '?')}</div>
            </div>
            <div class="meta-card">
                <div class="label">关注数</div>
                <div class="value">{meta.get('following', '?')}</div>
            </div>
            <div class="meta-card">
                <div class="label">分析推文数</div>
                <div class="value">{meta.get('tweets_analyzed', '?')}</div>
            </div>
            <div class="meta-card">
                <div class="label">评估时间</div>
                <div class="value" style="font-size: 0.85em;">{meta.get('scored_at', '')[-8:]}</div>
            </div>
        </div>

        <h3 style="margin: 16px 0 8px 0;">📋 6维度风险评分</h3>
        {dim_html}

        <h3 style="margin: 16px 0 8px 0;">🔍 风险详情</h3>
        <ul class="detail-list">
            {detail_html}
        </ul>

        <div class="rec-box">
            <strong>💡 建议：</strong> {recommendation}
        </div>
    </div>'''

# 主程序
results = {}
for acc in accounts:
    risk_file = f'F:\\Users\\Administrator\\Documents\\WorkBuddy\\2026-07-24-21-36-14\\data\\{acc}_risk_final.json'
    if os.path.exists(risk_file):
        with open(risk_file, encoding='utf-8') as f:
            results[acc] = json.load(f)

# 汇总表
summary_rows = ''
sorted_results = sorted(results.items(), key=lambda x: -x[1]['score'])
for acc, r in sorted_results:
    meta = r['meta']
    score = r['score']
    level = r['level']
    color, _, icon = level_colors.get(level, ('#6b7280', '#f3f4f6', '⚪'))
    summary_rows += f'''
    <tr>
        <td><strong>{meta.get('handle', '@' + acc)}</strong></td>
        <td><span style="color: {color}; font-weight: bold;">{icon} {score}/100</span></td>
        <td>{level}</td>
        <td>{meta.get('tweets_analyzed', '?')}</td>
        <td>{meta.get('followers', '?')}</td>
    </tr>'''

# 生成完整HTML
today = datetime.now().strftime('%Y-%m-%d %H:%M')
html = HTML_HEAD.replace('__DATE__', today)
html += f'''
<div class="summary">
<h2 style="margin-bottom: 16px;">📋 评分总览</h2>
<table>
<thead>
<tr>
<th>账号</th>
<th>分数</th>
<th>等级</th>
<th>分析推文</th>
<th>粉丝数</th>
</tr>
</thead>
<tbody>
{summary_rows}
</tbody>
</table>
</div>
'''

# 详细卡片
for acc, result in sorted_results:
    html += render_account(acc, result)

html += '''
<div class="footer">
报告由 X 账号风险监控系统 v3 自动生成 | 评分权重: 内容标记合规40% + 禁止内容25% + 行为真实性15% + 账号环境10% + 举报历史5% + 其他合规5%
</div>
</div>
</body>
</html>'''

# 保存
output_file = r'F:\Users\Administrator\Documents\WorkBuddy\2026-07-24-21-36-14\data\reports\x_risk_5_accounts_2026-07-26.html'
with open(output_file, 'w', encoding='utf-8') as f:
    f.write(html)

print(f'报告已生成: {output_file}')
print(f'文件大小: {len(html)} 字节')
print(f'账号数: {len(results)}')
for acc, r in sorted_results:
    print(f'  @{acc}: {r["score"]}/100 ({r["level"]})')