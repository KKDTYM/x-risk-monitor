#!/usr/bin/env python3
"""生成两个正式监控账号的v4 HTML报告"""
import json
import sys

# 加载v4结果
with open(r"F:\Users\Administrator\Documents\WorkBuddy\2026-07-24-21-36-14\data\dangao0709_risk_v4.json", encoding="utf-8") as f:
    dangao = json.load(f)
with open(r"F:\Users\Administrator\Documents\WorkBuddy\2026-07-24-21-36-14\data\kaixintangtang_risk_v4.json", encoding="utf-8") as f:
    kaixin = json.load(f)

accounts = [dangao, kaixin]

def get_color(level):
    if level == "high": return "#ef4444"
    if level == "medium": return "#f59e0b"
    return "#22c55e"

def level_text(level):
    if level == "high": return "高风险"
    if level == "medium": return "中等风险"
    return "低风险"

dim_names = {
    "marking": "内容标记合规",
    "prohibited": "禁止内容零触碰",
    "behavior": "行为真实性",
    "environment": "账号环境",
    "report_history": "举报历史",
    "other_compliance": "其他规则合规",
}

html_parts = []
html_parts.append("""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>X账号风险评估报告 - 2026-07-26 (v4)</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: #f3f4f6; color: #111827; line-height: 1.6; padding: 24px;
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
    padding: 24px 32px; display: flex; align-items: center; justify-content: space-between;
    border-bottom: 1px solid #e5e7eb;
}
.account-handle { font-size: 1.4em; font-weight: 700; }
.account-score {
    font-size: 2em; font-weight: 800; display: flex; align-items: baseline; gap: 4px;
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
.dimension-fill { height: 100%; border-radius: 4px; }
.dimension-issues { margin-top: 8px; }
.dimension-issues li { margin: 4px 0; font-size: 0.9em; color: #374151; }
.details-section { padding: 0 32px 24px; }
.detail-list { list-style: none; padding: 0; }
.detail-list li { padding: 8px 12px; margin: 4px 0; background: #f9fafb; border-radius: 6px; }
.recommendation {
    margin: 16px 0; padding: 16px; background: #eff6ff; border-radius: 8px;
    border-left: 4px solid #3b82f6;
}
footer { text-align: center; color: #6b7280; padding: 32px; font-size: 0.9em; }
</style>
</head>
<body>
<div class="container">
<div class="header">
<h1>X账号风险评估报告</h1>
<p class="date">v4 &middot; 2026-07-26 &middot; 基于更新后评分引擎（含硬转推占比/时间CV/Banner NSFW检测）</p>
</div>
""")

for acc in accounts:
    color = get_color(acc["level"])
    score = acc["score"]
    level = acc["level"]
    handle_line = acc["details"][0] if acc["details"] else "未知账号"

    html_parts.append(f"""
<div class="account-card">
    <div class="account-header">
        <div>
            <div class="account-handle">{handle_line}</div>
            <span class="level-badge" style="background: {color}">{level_text(level)}</span>
        </div>
        <div class="account-score" style="color: {color}">
            <span class="num">{score}</span><span class="max">/100</span>
        </div>
    </div>
    <div class="dimensions-grid">
""")

    dims = acc["dimensions"]
    for dim_key in ["marking", "prohibited", "behavior", "environment", "report_history", "other_compliance"]:
        d = dims[dim_key]
        risk = d["risk_score"]
        max_r = d["max_risk"]
        pct = min(risk / max_r * 100, 100) if max_r > 0 else 0
        fill_color = "#22c55e" if pct < 40 else "#f59e0b" if pct < 70 else "#ef4444"
        dim_label = dim_names.get(dim_key, dim_key)

        html_parts.append(f"""
        <div class="dimension-card">
            <div class="dimension-title">
                <span>{dim_label}</span>
                <span class="dimension-score" style="color: {fill_color}">{risk}/{max_r}</span>
            </div>
            <div class="dimension-bar">
                <div class="dimension-fill" style="width: {pct}%; background: {fill_color};"></div>
            </div>
            <ul class="dimension-issues">
""")
        for issue in d.get("issues", []):
            html_parts.append(f"<li>{issue}</li>")
        html_parts.append("</ul></div>")  # end dimension-card

    # Details section
    html_parts.append("</div><div class=\"details-section\">")
    html_parts.append('<ul class="detail-list">')
    for detail in acc["details"]:
        html_parts.append(f"<li>{detail}</li>")
    html_parts.append("</ul>")
    html_parts.append(f'<div class="recommendation"><strong>建议：</strong>{acc["recommendation"]}</div></div></div>')

html_parts.append("""
<footer>X 账号风险监控系统 &middot; v4 (2026-07-26) &middot; 评分引擎含硬转推占比/时间CV/Banner NSFW检测</footer>
</div>
</body>
</html>""")

output_path = r"F:\Users\Administrator\Documents\WorkBuddy\2026-07-24-21-36-14\dangao0709_and_kaixintangtang_risk_v4.html"
with open(output_path, "w", encoding="utf-8") as f:
    f.write("\n".join(html_parts))

print(f"Report saved to: {output_path}")
