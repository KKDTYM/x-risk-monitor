#!/usr/bin/env python3
"""Generate a standalone HTML risk report for @Conny_vv."""
import json, os, datetime

BASE = os.path.dirname(os.path.abspath(__file__))
data = json.load(open(f"{BASE}/conny_vv_risk_result.json", encoding="utf-8"))

profile = data["profile"]
sc = data["scores"]
dims = data["dimensions"]

LEVEL_COLORS = {"low": "#22c55e", "medium": "#f59e0b", "high": "#ef4444"}
LEVEL_NAMES = {"low": "低", "medium": "中", "high": "高"}

def bar(label, val, maxv, color):
    pct = min(100, round(val / maxv * 100))
    return f"""
    <div class="dim-row">
      <div class="dim-label">{label}</div>
      <div class="dim-track"><div class="dim-fill" style="width:{pct}%;background:{color};"></div></div>
      <div class="dim-val">{val}/{maxv}</div>
    </div>"""

MAXMAP = {"账号状态": 15, "安全红线": 25, "操纵指数": 20, "敏感内容": 25, "内容质量": 15}
COLOR_BY_DIM = {"账号状态": "#3b82f6", "安全红线": "#ef4444", "操纵指数": "#8b5cf6",
                "敏感内容": "#ec4899", "内容质量": "#14b8a6"}

a = sc["formal_empty_tweets"]
b = sc["augmented_with_bio"]
dims_a = dims["empty_tweets"]
dims_b = dims["with_bio_tweet"]

bars_a = "".join(bar(k, dims_a[k], MAXMAP[k], COLOR_BY_DIM[k]) for k in MAXMAP)
bars_b = "".join(bar(k, dims_b[k], MAXMAP[k], COLOR_BY_DIM[k]) for k in MAXMAP)

# Bio 信号高亮
bio = profile.get("description", "")
signals = ["Ts Shanghai Trans", "真发女声 36D", "线下", "全国可✈️", "口令私信", "解锁", "领课表", "tg："]
for s in signals:
    bio_hl = bio.replace(s, f'<mark>{s}</mark>')
# safe replace loop
bio_hl = bio
for s in signals:
    bio_hl = bio_hl.replace(s, f'<mark>{s}</mark>')
bio_hl = bio_hl.replace("\n", "<br>")

date_str = datetime.date.today().isoformat()

html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>@Conny_vv 风险评估报告 - {date_str}</title>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;
         background:#f3f4f6; color:#111827; line-height:1.6; padding:24px; }}
  .container {{ max-width:1000px; margin:0 auto; }}
  .header {{ background:white; padding:32px; border-radius:12px; box-shadow:0 2px 8px rgba(0,0,0,.1);
            margin-bottom:24px; text-align:center; }}
  .header h1 {{ font-size:2em; margin-bottom:6px; }}
  .header .date {{ color:#6b7280; }}
  .note {{ background:#fef3c7; border-left:4px solid #f59e0b; padding:14px 18px; border-radius:8px;
          margin-bottom:24px; font-size:.92em; color:#92400e; }}
  .card {{ background:white; padding:24px; border-radius:12px; box-shadow:0 2px 8px rgba(0,0,0,.1);
          margin-bottom:24px; }}
  .card h2 {{ margin-bottom:16px; padding-bottom:10px; border-bottom:2px solid #e5e7eb; }}
  .info-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:14px; }}
  .info-card {{ padding:14px; background:#f9fafb; border-radius:8px; text-align:center; }}
  .info-card .lbl {{ font-size:.8em; color:#6b7280; }}
  .info-card .val {{ font-size:1.4em; font-weight:bold; }}
  .score-flex {{ display:flex; gap:20px; flex-wrap:wrap; }}
  .score-box {{ flex:1; min-width:260px; padding:20px; border-radius:10px; background:#f9fafb;
               border:1px solid #e5e7eb; }}
  .score-box .big {{ font-size:2.6em; font-weight:bold; }}
  .badge {{ display:inline-block; padding:6px 16px; border-radius:14px; color:white; font-weight:bold; margin-top:8px; }}
  .dim-row {{ display:flex; align-items:center; gap:12px; margin:10px 0; }}
  .dim-label {{ width:80px; font-size:.9em; color:#374151; }}
  .dim-track {{ flex:1; height:14px; background:#e5e7eb; border-radius:7px; overflow:hidden; }}
  .dim-fill {{ height:100%; border-radius:7px; }}
  .dim-val {{ width:60px; text-align:right; font-size:.85em; color:#6b7280; }}
  mark {{ background:#fde68a; padding:0 2px; border-radius:3px; }}
  .bio-box {{ background:#fffbeb; border-left:4px solid #f59e0b; padding:14px 18px; border-radius:8px;
             font-size:.95em; line-height:1.8; }}
  ul.clean {{ list-style:none; padding:0; }}
  ul.clean li {{ padding:6px 0; border-bottom:1px dashed #e5e7eb; }}
  .rec {{ padding:16px; background:#eff6ff; border-left:4px solid #3b82f6; border-radius:8px; }}
  .footer {{ text-align:center; color:#9ca3af; font-size:.85em; padding:20px; }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>🛡️ @{data['username']} 风险评估报告</h1>
    <div class="date">报告日期：{date_str}</div>
  </div>

  <div class="note">
    ⚠️ <b>数据限制说明：</b>当前 X 平台对本环境登录及公开 API 全面限流，无法抓取 @{data['username']} 的真实推文。
    本报告基于 Fxtwitter 公开资料（profile + bio）评估。下方提供两个版本：版本 A 为保守估计（无推文），
    版本 B 将 bio 纳入推文样本，更接近真实风险。建议限流解除后重新拉取完整推文复评。
  </div>

  <div class="card">
    <h2>账号概览</h2>
    <div class="info-grid">
      <div class="info-card"><div class="lbl">名称</div><div class="val" style="font-size:1.05em;">{profile.get('name','')}</div></div>
      <div class="info-card"><div class="lbl">粉丝数</div><div class="val">{profile.get('followers_count','N/A')}</div></div>
      <div class="info-card"><div class="lbl">关注数</div><div class="val">{profile.get('following_count','N/A')}</div></div>
      <div class="info-card"><div class="lbl">推文数</div><div class="val">{profile.get('tweets_count','N/A')}</div></div>
      <div class="info-card"><div class="lbl">地点</div><div class="val" style="font-size:1.05em;">{profile.get('location','N/A')}</div></div>
      <div class="info-card"><div class="lbl">账号状态</div><div class="val" style="color:#22c55e;">正常</div></div>
    </div>
    <p style="margin-top:14px; color:#6b7280; font-size:.88em;">加入时间：{profile.get('joined','N/A')} ｜ 媒体数高（视觉化内容占比大）</p>
  </div>

  <div class="card">
    <h2>风险评分（双版本）</h2>
    <div class="score-flex">
      <div class="score-box">
        <div style="color:#6b7280; font-size:.9em;">版本 A · 正式（仅 profile，无推文）</div>
        <div class="big" style="color:{LEVEL_COLORS[a['level']]};">{a['score']}/100</div>
        <span class="badge" style="background:{LEVEL_COLORS[a['level']]};">风险等级：{LEVEL_NAMES[a['level']]}</span>
      </div>
      <div class="score-box">
        <div style="color:#6b7280; font-size:.9em;">版本 B · 增强（bio 合成推文样本）</div>
        <div class="big" style="color:{LEVEL_COLORS[b['level']]};">{b['score']}/100</div>
        <span class="badge" style="background:{LEVEL_COLORS[b['level']]};">风险等级：{LEVEL_NAMES[b['level']]}</span>
      </div>
    </div>
    <p style="margin-top:14px; color:#6b7280; font-size:.88em;">
      真实分数应介于两版之间或更高——实际成人推文会进一步推高「敏感内容」「安全红线」维度。
    </p>
  </div>

  <div class="card">
    <h2>风险维度拆解</h2>
    <h3 style="margin:8px 0 12px; color:#6b7280; font-size:.95em;">版本 A（空推文）</h3>
    {bars_a}
    <h3 style="margin:20px 0 12px; color:#6b7280; font-size:.95em;">版本 B（bio 合成推文）</h3>
    {bars_b}
  </div>

  <div class="card">
    <h2>Bio 强风险信号</h2>
    <div class="bio-box">{bio_hl}</div>
    <p style="margin-top:12px; font-size:.88em; color:#6b7280;">
      高亮词：TS 成人服务标识、线下见面、付费解锁/口令、TG 跨平台引流 —— 属典型成人服务推广特征。
    </p>
  </div>

  <div class="card">
    <h2>风险详情与建议</h2>
    <ul class="clean">
      {''.join(f'<li>🔸 {d}</li>' for d in data.get('details_augmented', []))}
    </ul>
    <div class="rec" style="margin-top:16px;">
      <strong>建议：</strong>待 X 登录限流解除后（通常数小时），用 <code>@GuodongW18138</code> 登录重新拉取完整推文，
      以得出精确分数。当前判断为 <b>中等风险（MEDIUM）</b>，建议纳入临时测试账号持续观察。
    </div>
  </div>

  <div class="footer">
    报告由 X 账号风险监控系统自动生成 ｜ 数据来源：Fxtwitter 公开资料 ｜ 生成时间：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}
  </div>
</div>
</body>
</html>"""

out = f"{BASE}/conny_vv_report.html"
with open(out, "w", encoding="utf-8") as f:
    f.write(html)
print("SAVED:", out, "size:", len(html))
