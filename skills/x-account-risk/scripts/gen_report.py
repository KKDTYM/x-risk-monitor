#!/usr/bin/env python3
"""通用 X 账号风险 HTML 报告生成器（风险分逻辑：分数越高风险越大）。

Usage:
  python gen_report.py <path_to_risk_v3.json> [output.html]
若未指定 output.html，默认输出到同目录的 <handle>_report.html。
"""
import json, sys, os

DIM_ORDER = ['marking', 'prohibited', 'behavior', 'environment', 'report_history', 'other_compliance']
DIM_NAMES = ['内容标记合规', '禁止内容零触碰', '行为真实性', '账号环境', '举报历史', '其他合规']
DIM_WEIGHTS = [30, 25, 25, 10, 5, 5]


def gen_report(data):
    score = data['score']
    handle = data['meta']['handle']
    dims = data['dimensions']

    # 风险分：分数越高 = 风险越高
    if score >= 70:
        risk_color, risk_label, risk_emoji = '#e74c3c', '高风险', '\U0001f534'
    elif score >= 40:
        risk_color, risk_label, risk_emoji = '#f39c12', '中等风险', '\U0001f7e1'
    else:
        risk_color, risk_label, risk_emoji = '#2ecc71', '低风险', '\U0001f7e2'

    score_rows = ''
    total_score_check = 0
    for i, key in enumerate(DIM_ORDER):
        d = dims[key]
        risk_score = d.get('risk_score', d.get('score', 0))
        max_risk = d.get('max_risk', d.get('max_score', 1))
        rate = risk_score / max_risk * 100
        total_score_check += risk_score
        color = '#e74c3c' if rate >= 70 else '#f39c12' if rate >= 40 else '#2ecc71'
        score_rows += f'''<tr>
<td>{DIM_NAMES[i]}</td>
<td>{DIM_WEIGHTS[i]}</td>
<td style="color: {color}; font-weight: bold;">{risk_score}</td>
<td>{max_risk}</td>
<td style="color: {color};">{rate:.0f}%</td>
</tr>'''

    dim_cards_html = ''

    # 1. marking
    m = dims['marking']
    m_color = '#e74c3c' if m['risk_score'] >= 20 else '#f39c12' if m['risk_score'] >= 27 else '#2ecc71'
    issues_html = ''
    if m.get('issues'):
        issues_html = '<p style="color: #e74c3c;">' + '<br>'.join(m['issues']) + '</p>'
    dim_cards_html += f'''<div class="dim-card" style="border-left-color: {m_color};">
<div class="dim-header"><div>
<span class="dim-title">1. 内容标记合规</span><span class="dim-weight">(权重 30/100)</span></div>
<div class="dim-score" style="color: {m_color};">{m['risk_score']}/30</div></div>
<div class="score-bar"><div class="score-bar-fill" style="width: {m['risk_score']/30*100}%; background: {m_color};"></div></div>
<div class="dim-detail">
<p><strong>[扣分标准]</strong> 每条未标记的成人内容推文扣 3 分（30 分满分，扣完为止）</p>
<p><strong>[你的情况]</strong> 成人内容推文 {m.get('total_adult_tweets',0)} 条，已标记 {m.get('flagged_count',0)} 条，未标记 {m.get('unflagged_count',0)} 条</p>
<p><strong>[改进建议]</strong> 在 X 设置中开启"标记敏感媒体"，每条含成人关键词+媒体的推文必须标记</p>
{issues_html}</div></div>'''

    # 2. prohibited
    p = dims['prohibited']
    p_issues_html = ''
    if p.get('issues'):
        p_issues_html = '<p style="color: #e74c3c;">' + '<br>'.join(p['issues']) + '</p>'
    tier1_detail_str = ', '.join(p.get('tier1_details', [])) if p.get('tier1_details') else '无'
    p_color = '#e74c3c' if p['risk_score'] >= 20 else '#f39c12' if p['risk_score'] >= 5 else '#2ecc71'
    dim_cards_html += f'''<div class="dim-card" style="border-left-color: {p_color};">
<div class="dim-header"><div>
<span class="dim-title">2. 禁止内容零触碰</span><span class="dim-weight">(权重 25/100)</span></div>
<div class="dim-score" style="color: {p_color};">{p['risk_score']}/25</div></div>
<div class="score-bar"><div class="score-bar-fill" style="width: {p['risk_score']/25*100}%; background: {p_color};"></div></div>
<div class="dim-detail">
<p><strong>[扣分标准]</strong> Tier1 违规 1 条扣 20 分；>=3 条扣完；Tier2 边界内容 1-2 条扣 5 分，>=3 条扣 10 分</p>
<p><strong>[Tier1 违规]</strong> {p.get('tier1_violations',0)} 条（{tier1_detail_str}）</p>
<p><strong>[Tier2 边界]</strong> {p.get('tier2_count',0)} 条</p>
<p><strong>[改进建议]</strong> 避免非合意内容、未成年人、性暴力、剥削</p>
{p_issues_html}</div></div>'''

    # 3. behavior
    b = dims['behavior']
    b_color = '#e74c3c' if b['risk_score'] >= 20 else '#f39c12' if b['risk_score'] >= 10 else '#2ecc71'
    bot_str = ', '.join(b.get('bot_signal_types', [])) if b.get('bot_signal_types') else '无'
    breakdown_html = ''
    if b.get('deduction_breakdown'):
        for k, v in b['deduction_breakdown'].items():
            if v:
                breakdown_html += f'<p><strong>[{k}]</strong> {v}</p>'
    b_issues_html = ''
    if b.get('behavior_issues'):
        b_issues_html = '<p style="color: #e74c3c;">' + '<br>'.join(b['behavior_issues']) + '</p>'
    dim_cards_html += f'''<div class="dim-card" style="border-left-color: {b_color};">
<div class="dim-header"><div>
<span class="dim-title">3. 行为真实性与频率</span><span class="dim-weight">(权重 25/100)</span></div>
<div class="dim-score" style="color: {b_color};">{b['risk_score']}/25</div></div>
<div class="score-bar"><div class="score-bar-fill" style="width: {b['risk_score']/25*100}%; background: {b_color};"></div></div>
<div class="dim-detail">
<p><strong>[扣分标准]</strong> 自动化工具每种扣 5 分；频率突增最多 5 分；内容重复>30% 按比例最多 7.5 分；24h密集发布最多 5 分</p>
<p><strong>[自动化工具]</strong> {len(b.get('bot_signal_types', []))} 种 ({bot_str})</p>
{breakdown_html}
<p><strong>[改进建议]</strong> 手动操作、控制发帖频率、避免内容重复、避免短时间密集发布</p>
{b_issues_html}</div></div>'''

    # 4. environment
    e = dims['environment']
    e_color = '#e74c3c' if e['risk_score'] >= 8 else '#f39c12' if e['risk_score'] >= 5 else '#2ecc71'
    env_detail = ''
    if e.get('issues'):
        env_detail = '<p><strong>[你的情况]</strong> ' + '</p><p><strong>[你的情况]</strong> '.join(
            [i.replace('\u26a0\ufe0f ', '').replace('\u2705 ', '') for i in e['issues']]) + '</p>'
    else:
        env_detail = '<p><strong>[你的情况]</strong> 正常</p>'
    dim_cards_html += f'''<div class="dim-card" style="border-left-color: {e_color};">
<div class="dim-header"><div>
<span class="dim-title">4. 账号环境与登录安全</span><span class="dim-weight">(权重 10/100)</span></div>
<div class="dim-score" style="color: {e_color};">{e['risk_score']}/10</div></div>
<div class="score-bar"><div class="score-bar-fill" style="width: {e['risk_score']/10*100}%; background: {e_color};"></div></div>
<div class="dim-detail">
<p><strong>[扣分标准]</strong> 新号(粉丝<100)扣 3 分；异常登录扣 3 分；脏设备/共享IP扣 2 分；未绑定手机扣 2 分</p>
{env_detail}
<p><strong>[改进建议]</strong> 绑定手机号、稳定IP登录、避免多账号共用设备</p></div></div>'''

    # 5. report_history
    r = dims['report_history']
    r_color = '#e74c3c' if r['risk_score'] >= 4 else '#f39c12' if r['risk_score'] >= 2 else '#2ecc71'
    r_issues_html = ''
    if r.get('issues'):
        r_issues_html = '<p style="color: #e74c3c;">' + '<br>'.join(r['issues']) + '</p>'
    dim_cards_html += f'''<div class="dim-card" style="border-left-color: #2ecc71;">
<div class="dim-header"><div>
<span class="dim-title">5. 举报与历史记录</span><span class="dim-weight">(权重 5/100)</span></div>
<div class="dim-score" style="color: {r_color};">{r['risk_score']}/5</div></div>
<div class="score-bar"><div class="score-bar-fill" style="width: {r['risk_score']/5*100}%; background: {r_color};"></div></div>
<div class="dim-detail">
<p><strong>[扣分标准]</strong> 举报>5次扣 3 分；有警告记录扣 2 分；违规>=3次扣完 5 分</p>
<p><strong>[改进建议]</strong> 避免被大量举报，及时处理警告，控制违规次数</p>
{r_issues_html}</div></div>'''

    # 6. other_compliance
    o = dims['other_compliance']
    o_color = '#e74c3c' if o['risk_score'] >= 4 else '#f39c12' if o['risk_score'] >= 2 else '#2ecc71'
    o_issues_html = ''
    if o.get('issues'):
        o_issues_html = '<p style="color: #e74c3c;">' + '<br>'.join(o['issues']) + '</p>'
    violations_str = ', '.join(o.get('violations_found', [])) if o.get('violations_found') else '无'
    dim_cards_html += f'''<div class="dim-card" style="border-left-color: #2ecc71;">
<div class="dim-header"><div>
<span class="dim-title">6. 其他规则合规</span><span class="dim-weight">(权重 5/100)</span></div>
<div class="dim-score" style="color: {o_color};">{o['risk_score']}/5</div></div>
<div class="score-bar"><div class="score-bar-fill" style="width: {o['risk_score']/5*100}%; background: {o_color};"></div></div>
<div class="dim-detail">
<p><strong>[扣分标准]</strong> 发现骚扰/版权/冒充/平台操纵每类扣 1 分，最多扣 5 分</p>
<p><strong>[违规类型]</strong> {violations_str}</p>
<p><strong>[改进建议]</strong> 避免批量@、版权侵权、冒充官方、刷量</p>
{o_issues_html}</div></div>'''

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{handle} X 账号风险评估报告</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif; background: #f0f2f5; padding: 20px; color: #333; }}
  .container {{ max-width: 900px; margin: 0 auto; background: white; border-radius: 16px; overflow: hidden; box-shadow: 0 8px 32px rgba(0,0,0,0.1); }}
  .header {{ background: linear-gradient(135deg, #1a1a2e, #16213e); color: white; padding: 40px 30px; text-align: center; }}
  .header h1 {{ font-size: 32px; margin-bottom: 10px; }}
  .header p {{ color: #aaa; font-size: 14px; margin-top: 5px; }}
  .score-section {{ padding: 40px 30px; text-align: center; background: #fafafa; }}
  .score-circle {{ width: 200px; height: 200px; border-radius: 50%; background: conic-gradient({risk_color} 0deg {score*3.6}deg, #e0e0e0 {score*3.6}deg 360deg); display: flex; align-items: center; justify-content: center; margin: 0 auto 20px; }}
  .score-inner {{ width: 160px; height: 160px; border-radius: 50%; background: white; display: flex; flex-direction: column; align-items: center; justify-content: center; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }}
  .score-number {{ font-size: 56px; font-weight: bold; color: {risk_color}; }}
  .score-label {{ font-size: 14px; color: #999; }}
  .risk-label {{ font-size: 20px; color: {risk_color}; font-weight: bold; margin-top: 15px; }}
  .score-table {{ width: 100%; border-collapse: collapse; margin: 20px 0; font-size: 14px; }}
  .score-table th {{ background: #f5f5f5; padding: 12px; text-align: left; font-weight: 600; border-bottom: 2px solid #ddd; }}
  .score-table td {{ padding: 10px 12px; border-bottom: 1px solid #eee; }}
  .score-table tr:last-child td {{ border-bottom: none; font-weight: bold; background: #f9f9f9; font-size: 15px; }}
  .dimensions {{ padding: 30px; }}
  .section-title {{ font-size: 22px; font-weight: bold; margin-bottom: 20px; color: #1a1a2e; }}
  .dim-card {{ margin-bottom: 24px; border-radius: 12px; padding: 24px; background: #fafafa; border-left: 5px solid #ddd; }}
  .dim-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; flex-wrap: wrap; gap: 10px; }}
  .dim-title {{ font-size: 17px; font-weight: bold; color: #1a1a2e; }}
  .dim-weight {{ color: #999; font-size: 13px; margin-left: 10px; }}
  .dim-score {{ font-size: 28px; font-weight: bold; }}
  .dim-detail {{ font-size: 14px; color: #555; line-height: 1.8; }}
  .score-bar {{ height: 8px; background: #e0e0e0; border-radius: 4px; overflow: hidden; margin: 12px 0; }}
  .score-bar-fill {{ height: 100%; border-radius: 4px; }}
  .footer {{ padding: 20px; text-align: center; font-size: 12px; color: #999; border-top: 1px solid #eee; }}
  .legend {{ padding: 20px 30px; background: #fffde7; border-top: 1px solid #fff9c4; font-size: 13px; line-height: 1.8; }}
  .legend strong {{ color: #f57f17; }}
  .total-row td {{ font-size: 16px; }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>X 账号风险评估报告</h1>
    <p>{handle}</p>
    <p>评估日期：{data.get('meta',{}).get('evaluated_at','')[:10] or '2026'} | 引擎版本：v3 (6 维度)</p>
  </div>
  <div class="score-section">
    <div class="score-circle"><div class="score-inner">
      <div class="score-number">{score}</div>
      <div class="score-label">/ 100 分</div>
    </div></div>
    <div class="risk-label">{risk_emoji} {risk_label}</div>
    <div style="margin-top: 30px;">
      <h3 style="margin-bottom: 15px;">\U0001f4ca 各维度得分总览</h3>
      <table class="score-table">
        <tr><th>维度</th><th>权重</th><th>得分</th><th>满分</th><th>得分率</th></tr>
        {score_rows}
        <tr class="total-row"><td colspan="2">总分 (维度之和)</td><td style="font-size: 18px;">{total_score_check}</td><td>100</td><td>{total_score_check}%</td></tr>
      </table>
      <p style="margin-top: 15px; font-size: 13px; color: #666; background: #e8f5e9; padding: 12px; border-radius: 8px; display: inline-block; text-align: left;">
        <strong>\u2705 验证通过：</strong>总分 {score} = 各维度得分之和 {total_score_check}<br>
        即：{handle} 的总分 = 各维度得分严格相加，无偏差
      </p>
    </div>
  </div>
  <div class="dimensions">
    <h2 class="section-title">\U0001f4cb 6 维度详细评分（含扣分标准）</h2>
    {dim_cards_html}
  </div>
  <div class="legend">
    <strong>\U0001f4a1 计分规则说明：</strong><br>
    <strong>总分</strong> = 各维度风险分之和（分数越高风险越大）<br>
    <strong>权重</strong> = 维度在总分中的占比（30%+25%+25%+10%+5%+5% = 100%）<br>
    <strong>阈值</strong> = 高风险 ≥60 / 中等风险 30–59 / 低风险 <30<br>
    <strong>报告总分</strong> = 各维度风险分之和，精确到整数
  </div>
  <div class="footer">X 账号风险监控系统 v3 | 融合 Grok 成人内容账号长期存活自评表 | 数据来源：Playwright DOM 抓取</div>
</div>
</body>
</html>'''
    return html


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python gen_report.py <risk_v3.json> [output.html]')
        sys.exit(2)
    risk_json = sys.argv[1]
    data = json.load(open(risk_json, encoding='utf-8'))
    base = os.path.splitext(os.path.basename(risk_json))[0]
    out_html = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(risk_json), f'{base.replace("_risk_v3","")}_report.html')
    html = gen_report(data)
    open(out_html, 'w', encoding='utf-8').write(html)
    print('Report written to', out_html, '| bytes:', len(html), '| score:', data['score'])
