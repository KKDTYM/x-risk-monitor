#!/usr/bin/env python3
import json

WS = 'F:/Users/Administrator/Documents/WorkBuddy/2026-07-24-21-36-14'
data = json.load(open(f'{WS}/conny_vv_risk_real.json', encoding='utf-8'))

score = data['score']
level = data['level']
dims = data['dimensions']
meta = data['meta']
tweets = data.get('tweets', [])
rec = data['recommendation']
details = data.get('details', [])

LEVEL_COLOR = {'high': '#e53935', 'medium': '#fb8c00', 'low': '#43a047'}
color = LEVEL_COLOR.get(level, '#fb8c00')

# highlight bio signals
bio = meta.get('bio', '')
HIGHLIGHT = ['线下', '全国可', '口令', '私信', '解锁', '领课表', 'tg', 'Ts', 'Trans', '36D', '真发女声', '上海']
def hl(text):
    for kw in HIGHLIGHT:
        text = text.replace(kw, f'<mark>{kw}</mark>')
    return text

# dimension bars
dim_meta = [
    ('账号状态', dims['account_status'], 15),
    ('安全红线', dims['safety_redline'], 25),
    ('操纵指数', dims['manipulation'], 20),
    ('敏感内容', dims['sensitive'], 25),
    ('内容质量', dims['content_quality'], 15),
]
bars = ''
for name, val, maxv in dim_meta:
    pct = min(val / maxv * 100, 100)
    bars += f'''
    <div class="dim">
      <div class="dim-head"><span>{name}</span><span>{val:.1f} / {maxv}</span></div>
      <div class="bar"><div class="fill" style="width:{pct:.1f}%;background:{color}"></div></div>
    </div>'''

# tweet list
tweet_html = ''
for i, t in enumerate(tweets[:15], 1):
    txt = t['text'].replace('<', '&lt;').replace('>', '&gt;')
    tweet_html += f'''
    <div class="tweet">
      <div class="t-num">#{i}</div>
      <div class="t-body">
        <div class="t-text">{txt}</div>
        <div class="t-meta">❤ {t['likes']} &nbsp; 🔁 {t['retweets']}</div>
      </div>
    </div>'''

details_html = ''.join(f'<li>{d}</li>' for d in details)

html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>@Conny_vv 风险评估报告</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, "Segoe UI", "Microsoft YaHei", sans-serif; background: #f4f6f9; color: #1a1a1a; line-height: 1.6; padding: 24px; }}
  .wrap {{ max-width: 880px; margin: 0 auto; }}
  .card {{ background: #fff; border-radius: 14px; padding: 24px; margin-bottom: 18px; box-shadow: 0 2px 12px rgba(0,0,0,.06); }}
  h1 {{ font-size: 22px; margin-bottom: 4px; }}
  .sub {{ color: #888; font-size: 13px; margin-bottom: 16px; }}
  .overview {{ display: flex; gap: 12px; flex-wrap: wrap; }}
  .ov {{ background: #f7f9fc; border-radius: 10px; padding: 10px 14px; font-size: 13px; }}
  .ov b {{ display: block; font-size: 18px; color: #333; }}
  .score-card {{ text-align: center; padding: 28px; }}
  .score-num {{ font-size: 64px; font-weight: 800; color: {color}; line-height: 1; }}
  .score-lvl {{ display: inline-block; margin-top: 8px; padding: 4px 16px; border-radius: 20px; background: {color}; color: #fff; font-weight: 600; font-size: 14px; }}
  .dim {{ margin: 14px 0; }}
  .dim-head {{ display: flex; justify-content: space-between; font-size: 13px; margin-bottom: 5px; color: #555; }}
  .bar {{ background: #eef1f5; border-radius: 8px; height: 12px; overflow: hidden; }}
  .fill {{ height: 100%; border-radius: 8px; }}
  mark {{ background: #fff3cd; padding: 0 2px; border-radius: 3px; font-weight: 600; }}
  .bio {{ background: #fffaf0; border-left: 4px solid #ffc107; padding: 12px 16px; border-radius: 8px; font-size: 14px; white-space: pre-wrap; }}
  .tweet {{ display: flex; gap: 10px; padding: 10px 0; border-bottom: 1px solid #f0f0f0; }}
  .t-num {{ color: #bbb; font-size: 12px; min-width: 28px; }}
  .t-text {{ font-size: 13px; white-space: pre-wrap; word-break: break-word; }}
  .t-meta {{ font-size: 12px; color: #999; margin-top: 4px; }}
  .note {{ background: #e3f2fd; border-radius: 8px; padding: 12px 16px; font-size: 13px; color: #1565c0; }}
  ul {{ margin: 8px 0 0 18px; font-size: 13px; color: #555; }}
  .rec {{ background: #fff3e0; border-radius: 8px; padding: 12px 16px; font-size: 14px; }}
</style>
</head>
<body>
<div class="wrap">

  <div class="card">
    <h1>{meta['handle']} 风险评估报告</h1>
    <div class="sub">{meta['name']} · 生成于 {meta['scored_at']}</div>
    <div class="overview">
      <div class="ov">粉丝<b>{meta['followers']}</b></div>
      <div class="ov">关注<b>{meta['following']}</b></div>
      <div class="ov">分析推文<b>{meta['tweets_analyzed']}</b></div>
      <div class="ov">数据源<b style="font-size:13px">{meta['data_source']}</b></div>
    </div>
  </div>

  <div class="card score-card">
    <div class="score-num">{score}</div>
    <div class="score-lvl">{level.upper()} · {'高风险' if level=='high' else '中风险' if level=='medium' else '低风险'}</div>
    <div style="margin-top:14px; font-size:13px; color:#777">满分 100 · 维度加权累加</div>
  </div>

  <div class="card">
    <h1 style="font-size:17px; margin-bottom:14px">风险维度拆解</h1>
    {bars}
  </div>

  <div class="card">
    <h1 style="font-size:17px; margin-bottom:12px">Bio 强信号</h1>
    <div class="bio">{hl(bio)}</div>
  </div>

  <div class="card">
    <h1 style="font-size:17px; margin-bottom:10px">推文样本（前 {min(len(tweets),15)} 条）</h1>
    {tweet_html}
  </div>

  <div class="card">
    <h1 style="font-size:17px; margin-bottom:10px">风险详情</h1>
    <ul>{details_html}</ul>
  </div>

  <div class="card rec">
    <b>处置建议：</b> {rec}
  </div>

  <div class="note">
    ⚠️ 说明：本次评分基于 Cookie 授权抓取的 <b>{meta['tweets_analyzed']} 条真实推文</b>（2022-07~08）。
    该账号 Fxtwitter 显示共有 37 条推文，X 网页端仅加载出 17 条（疑似部分敏感推文被折叠）。
    若需更精确评分，待可抓取完整推文列表后可一键复评。
  </div>

</div>
</body>
</html>'''

out = f'{WS}/conny_vv_report.html'
open(out, 'w', encoding='utf-8').write(html)
print('report written ->', out)
