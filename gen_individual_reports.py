"""
为每个账号生成独立的HTML评估报告
"""
import json
import os
from datetime import datetime

accounts = ['chichi_maddy', 'shutiaoniang', 'jiajia2475', 'sino11680908', 'VulpesM']

dim_names = {
    'marking': '内容标记合规',
    'prohibited': '禁止内容',
    'behavior': '行为真实性',
    'environment': '账号环境',
    'report_history': '举报历史',
    'other_compliance': '其他合规'
}

level_colors = {
    'high': ('#ef4444', '#fee2e2', '🔴 高风险'),
    'medium': ('#f59e0b', '#fef3c7', '🟡 中等风险'),
    'low': ('#22c55e', '#dcfce7', '🟢 低风险')
}

def render_single(acc, result):
    meta = result.get('meta', {})
    score = result['score']
    level = result['level']
    dims = result['dimensions']
    details = result['details']
    recommendation = result['recommendation']

    color, bg_color, level_text = level_colors.get(level, ('#6b7280', '#f3f4f6', '⚪ 未知'))

    # 渲染维度进度条
    dim_html = ''
    for dim_key, dim_data in dims.items():
        if not isinstance(dim_data, dict):
            continue
        risk = dim_data.get('risk_score', 0)
        max_risk = dim_data.get('max_risk', 1)
        pct = (risk / max_risk * 100) if max_risk > 0 else 0

        dim_cn = dim_names.get(dim_key, dim_key)
        issues = dim_data.get('issues', [])

        if pct >= 80:
            bar_color = '#ef4444'
        elif pct >= 40:
            bar_color = '#f59e0b'
        else:
            bar_color = '#22c55e'

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

        dim_html += f'''
        <div style="margin-bottom: 16px; padding: 12px; background: #f9fafb; border-radius: 8px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                <strong style="color: #1f2937;">{dim_cn}</strong>
                <span style="color: {bar_color}; font-weight: bold;">{risk}/{max_risk}</span>
            </div>
            <div class="bar-container">
                <div class="bar-fill" style="width: {pct:.1f}%; background: {bar_color};"></div>
            </div>
            {issues_html}
        </div>'''

    # 渲染详情列表
    detail_html = ''
    for d in details:
        if '⚠️' in str(d):
            detail_html += f'<li style="padding: 6px 0; color: #dc2626;">⚠️ {d}</li>'
        elif '✅' in str(d):
            detail_html += f'<li style="padding: 6px 0; color: #16a34a;">✅ {d}</li>'
        else:
            detail_html += f'<li style="padding: 6px 0; color: #4b5563;">• {d}</li>'

    bio = meta.get('bio', '')
    if len(bio) > 200:
        bio = bio[:200] + '...'

    today = datetime.now().strftime('%Y-%m-%d %H:%M')

    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>X账号风险评估报告 - {meta.get('handle', '@' + acc)}</title>
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
.bar-container {{ background: #e5e7eb; height: 10px; border-radius: 5px; overflow: hidden; }}
.bar-fill {{ height: 100%; transition: width 0.3s; }}
.detail-list {{ list-style: none; padding: 0; }}
.rec-box {{ margin-top: 16px; padding: 16px; border-radius: 8px; background: #f0f9ff; border-left: 4px solid #3b82f6; color: #1e40af; }}
.footer {{ text-align: center; padding: 24px; color: #9ca3af; font-size: 0.85em; }}
</style>
</head>
<body>
<div class="container">
<div class="header">
<h1>📊 X账号风险评估报告</h1>
<div class="date">{today} | 账号: {meta.get('handle', '@' + acc)}</div>
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
<div class="bio-text">{bio or "无"}</div>
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

# 主程序
for acc in accounts:
    risk_file = f'F:\\Users\\Administrator\\Documents\\WorkBuddy\\2026-07-24-21-36-14\\data\\{acc}_risk_final.json'
    if not os.path.exists(risk_file):
        print(f'@{acc}: 无评分数据，跳过')
        continue

    with open(risk_file, encoding='utf-8') as f:
        result = json.load(f)

    html = render_single(acc, result)

    out_file = f'F:\\Users\\Administrator\\Documents\\WorkBuddy\\2026-07-24-21-36-14\\data\\reports\\x_risk_{acc}_2026-07-26.html'
    with open(out_file, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f'✓ @{acc}: {out_file} ({len(html)} bytes)')

print('\n所有独立报告已生成。')