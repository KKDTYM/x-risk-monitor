#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""X 账号风险 HTML 报告生成器 v4.3（10 维度）。
Usage: python gen_report_v4.py <risk_json> [output.html]
"""
import html
import json
import os
import sys

DIMS = [
    ("acc_plan", "1. ACC 计划合规", 15,
     "检测是否加入 X Adult Content Creator 计划：未加入 +10；加入但未完善资料 +7；已完善 0（2026 年强制）。",
     "若经营成人内容，请加入 ACC 计划并完善资料，否则面临限流/封禁。"),
    ("marking", "2. ACC 三级标记合规", 15,
     "成人内容推文是否正确标记 Sensitive Media：每条未标记 +3（上限 15）。关键词：小穴、肉棒、男娘、femboy、ts、平胸、女仆、nsfw、18+ 等 50+ 词。",
     "含成人关键词+媒体的推文必须开启“标记敏感内容”，避免漏标。"),
    ("api_reply", "3. API 自动回复合规", 12,
     "API v2 2026 限制：自动回复必须提及/引用原作者（未提及 +3/次）；同一推文被回复 >10 次 +2/条；回复内容重复 >5 条 +3。",
     "使用 API 自动回复时引用原作者，控制回复频率与重复度。"),
    ("ip_network", "4. IP/网络环境合规", 10,
     "数据中心 IP（AWS/阿里云/腾讯云/Tor）+5；频繁 IP 切换（>5 个/周）+3；住宅 IP 正常。",
     "使用住宅 IP 登录，避免数据中心 IP 与频繁切换。"),
    ("shadowban", "5. Shadowban 隐形限制", 10,
     "搜索用户名无推文显示 +6；回复深度 <3 层 +3；印响数骤降 >50% +3；特定标签搜索无该账号推文 +4。",
     "检查搜索可见性与回复深度，避免被隐形限流。"),
    ("follow_ratio", "6. 关注/粉丝比与增长", 8,
     "关注/粉丝比 >10:1 +4（疑似关注轰炸）；粉丝中机器人占比 >30% +3；关注列表 >50% 被封账号 +2。",
     "保持关注/粉丝比正常，清理机器人粉与异常关注。"),
    ("premium", "7. Premium 会员等级", 8,
     "Premium Basic（$3/月）0；Premium（$8/月）-2 信任加分；Premium+（$200/月）-5；粉丝 >10K 未开通 +2。",
     "开通 Premium 提升账号信任度（负分=信任加分）。"),
    ("content_diversity", "8. 内容多样性与活跃度", 12,
     "单一 NSFW 内容 >80% +5；原创与搬运比 <1:3 +4；60% 推文在 2 小时内发布 +3；>70% 推文互动低（<5 赞）+3。",
     "增加原创内容，避免内容单一与短时刷屏，提升互动。"),
    ("prohibited", "9. 禁止内容零接触", 25,
     "Tier 1（非合意/未成年/性暴力/血腥剥刮）：1 条 +20，≥3 条 +25；Tier 2 边界（暗示）：1-2 条 +5，≥3 条 +10。",
     "严禁非合意/未成年/性暴力/血腥内容，控制擦边暗示。"),
    ("survival", "10. 账号存续风险", 15,
     "封禁/重生史信号（复活版/重生号/被冻/冻结/重开/旧号/被盗号等）+4/个（上限 8）；性交易/商业变现信号（接线下/可约/报价/课表/口令/门槛/付费/有偿/图包/电报/淘宝等）+3/个（上限 7，“无/不+词”的声明不扣）；隐私泄露/开盒信号 +5。",
     "被封过的号按原模式重启 = 再封高优先级；涉性交易与隐私泄露的号是平台与执法重点，建议立即整改运营模式。"),
]


def color_for(score, max_risk):
    rate = score / max_risk if max_risk else 0
    if rate >= 0.7:
        return "#e74c3c"
    if rate >= 0.4:
        return "#f39c12"
    return "#2ecc71"


def esc(s):
    return html.escape(str(s), quote=True)


def gen_report(data):
    score = data["score"]
    level = data["level"]
    meta = data.get("meta", {})
    handle = meta.get("handle", "")
    name = meta.get("name", "")
    tweets = data.get("tweets", [])
    dims = data["dimensions"]

    level_cn = {"high": "高风险", "medium": "中风险", "low": "低风险"}[level]
    risk_color = {"high": "#e74c3c", "medium": "#f39c12", "low": "#2ecc71"}[level]
    risk_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}[level]

    total_max = sum(d[2] for d in DIMS)

    # ---- 汇总表 ----
    score_rows = ""
    dim_total = 0
    for key, title, maxr, _crit, _sug in DIMS:
        d = dims.get(key, {})
        rs = d.get("risk_score", 0)
        dim_total += rs
        c = color_for(rs, maxr)
        rate = rs / maxr * 100
        score_rows += (
            f"<tr><td>{esc(title)}</td><td>{maxr}</td>"
            f'<td style="color:{c};font-weight:bold;">{rs}</td><td>{maxr}</td>'
            f'<td style="color:{c};">{rate:.0f}%</td></tr>'
        )
    score_rows += (
        f'<tr class="total-row"><td>合计（维度之和）</td><td>{total_max}</td>'
        f'<td>{dim_total}</td><td>{total_max}</td><td>{dim_total / total_max * 100:.0f}%</td></tr>'
    )

    # ---- 维度卡片 ----
    cards = ""
    for key, title, maxr, crit, sug in DIMS:
        d = dims.get(key, {})
        rs = d.get("risk_score", 0)
        c = color_for(rs, maxr)
        issues = d.get("issues", [])
        issues_html = ""
        for i in issues:
            issues_html += f"<p style='color:#c0392b;'>{esc(i)}</p>"
        if not issues_html:
            issues_html = "<p style='color:#2ecc71;'>未发现异常</p>"
        extra = ""
        if key == "prohibited":
            t2 = d.get("tier2_details", [])
            if t2:
                extra = "<p><strong>[Tier2 边界内容样例]</strong></p>" + "".join(
                    f"<p class='tweet-quote'>{esc(t[:100])}</p>" for t in t2
                )
        elif key == "content_diversity" and d.get("deduction_breakdown"):
            for k2, v2 in d["deduction_breakdown"].items():
                extra += f"<p><strong>[{esc(k2)}]</strong> {esc(v2)}</p>"
        cards += f"""
<div class="dim-card" style="border-left-color:{c};">
  <div class="dim-header">
    <div><span class="dim-title">{esc(title)}</span><span class="dim-weight">（权重 {maxr}/{total_max}）</span></div>
    <div class="dim-score" style="color:{c};">{rs}<span class="dim-max">/{maxr}</span></div>
  </div>
  <div class="score-bar"><div class="score-bar-fill" style="width:{rs / maxr * 100:.1f}%;background:{c};"></div></div>
  <div class="dim-detail">
    <p><strong>[扣分标准]</strong> {esc(crit)}</p>
    <p><strong>[你的情况]</strong></p>
    {issues_html}
    {extra}
    <p><strong>[改进建议]</strong> {esc(sug)}</p>
  </div>
</div>"""

    # ---- 推文样本表 ----
    tweet_rows = ""
    for t in tweets[:25]:
        text = (t.get("text") or "").replace("\n", " ")
        tweet_rows += (
            f"<tr><td>{esc((t.get('time') or '')[:10])}</td>"
            f'<td class="tweet-text">{esc(text[:100])}</td>'
            f"<td>{t.get('likes', 0)}</td><td>{t.get('retweets', 0)}</td>"
            f"<td>{t.get('views', 0)}</td>"
            f"<td>{'是' if t.get('hasMedia') else '否'}</td>"
            f"<td>{'是' if t.get('possibly_sensitive') else '否'}</td></tr>"
        )
    if not tweet_rows:
        tweet_rows = "<tr><td colspan='7'>无推文样本</td></tr>"

    n_analyzed = meta.get("tweets_analyzed", len(tweets))
    dates = sorted(t.get("time", "")[:10] for t in tweets if t.get("time"))
    d_from = dates[0] if dates else "-"
    d_to = dates[-1] if dates else "-"
    statuses = meta.get("statuses") or 0
    cover_pct = n_analyzed * 100 // max(1, statuses) if statuses else 100
    coverage = (
        f"<strong>已验证：</strong>登录态深度抓取（主时间线 + 回复标签页）合并去重后 {n_analyzed} 条本账号真实推文"
        f"（{d_from} ~ {d_to}，约占账号 {statuses} 条的 {cover_pct}%）、阅读量/互动/媒体/敏感标记、粉丝/关注/认证状态、"
        "搜索可见性实测（自动补全/用户搜索/from: 对照组）。<br>"
        "<strong>未验证（计 0 分，不扣也不减）：</strong>ACC 计划成员状态、API 自动回复日志、"
        "IP/网络环境、回复深度/印响骤降、粉丝机器人占比、Premium 具体档位、举报/违规历史。"
    )

    # ---- 数据驱动的关键发现 ----
    findings = []
    n_media = sum(1 for t in tweets if t.get("hasMedia"))
    n_sens = sum(1 for t in tweets if t.get("possibly_sensitive"))
    top_likes = max((t.get("likes", 0) or 0 for t in tweets), default=0)
    top_views = max((t.get("views", 0) or 0 for t in tweets), default=0)
    n_posts = sum(1 for t in tweets if not t.get("is_reply") and not t.get("is_retweet"))
    n_rt = sum(1 for t in tweets if t.get("is_retweet"))
    n_rep = sum(1 for t in tweets if t.get("is_reply") and not t.get("is_retweet"))
    h = meta.get("handle", "")

    if meta.get("profile_sensitive_warning"):
        findings.append(
            f"<p><strong>⚠️ X 官方敏感标记：</strong>该账号个人资料页显示“此个人资料可能包含潜在的敏感内容”警告门，"
            f"且 {n_sens}/{len(tweets)} 条已抓推文被 X 标记敏感——账号已被平台识别为成人内容账号。</p>"
        )
    findings.append(
        f"<p><strong>🔞 内容画像：</strong>已抓取 {len(tweets)} 条中 {n_media} 条含媒体、{n_sens} 条被 X 标记敏感"
        f"（{n_sens * 100 // max(1, len(tweets))}%），单条最高 {top_views:,} 阅读 / {top_likes:,} 赞；"
        "互动集中在主推文，回复类推文互动低。</p>"
    )
    st = meta.get("search_tests", {})
    if st.get("from_search_empty") and not st.get("from_search_works"):
        findings.append(
            f"<p><strong>🔍 搜索可见性：</strong>from:{h.lstrip('@')} 零结果（对照组同样为空，属查看者敏感过滤）；"
            "自动补全/用户搜索未出现真号。</p>"
        )
    elif st.get("from_search_works"):
        findings.append(
            f"<p><strong>🔍 搜索可见性：</strong>from:{h.lstrip('@')} 返回真实推文，自动补全含“前往 {h}”直达入口——"
            "账号可被正常搜索到，未被搜索限流；用户搜索前排未见精确真号。</p>"
        )
    else:
        findings.append(
            f"<p><strong>🔍 搜索可见性：</strong>实测自动补全与用户搜索“{h.lstrip('@')}”均不出现真号 {h}，"
            f"from:{h.lstrip('@')} 零结果（对照组同样为空，属查看者敏感过滤）。</p>"
        )
    findings.append(
        f"<p><strong>📊 原创/转帖构成：</strong>已抓取 {len(tweets)} 条中原创帖 {n_posts} 条、回复 {n_rep} 条、"
        f"转帖 {n_rt} 条；因 X 虚拟化滚动上限，未能加载的剩余推文推测为更早的回复/转帖（无法公开验证）。</p>"
    )
    imps = meta.get("impersonators") or []
    if imps:
        findings.append(
            f"<p><strong>🚨 仿冒提示：</strong>搜索中发现仿冒/近似账号：@{esc(', @'.join(imps))}，"
            "请注意甄别，避免仿冒号冒充本尊实施诈骗。</p>"
        )
    findings_html = '<div class="findings">' + "".join(findings) + "</div>"

    html_doc = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(handle)} X 账号风险评估报告</title>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family:'PingFang SC','Microsoft YaHei',sans-serif; background:#f0f2f5; padding:20px; color:#333; }}
  .container {{ max-width:960px; margin:0 auto; background:#fff; border-radius:16px; overflow:hidden; box-shadow:0 8px 32px rgba(0,0,0,.1); }}
  .header {{ background:linear-gradient(135deg,#1a1a2e,#16213e); color:#fff; padding:36px 30px; text-align:center; }}
  .header h1 {{ font-size:28px; margin-bottom:8px; }}
  .header p {{ color:#aaa; font-size:14px; margin-top:4px; }}
  .score-section {{ padding:36px 30px; text-align:center; background:#fafafa; }}
  .score-circle {{ width:200px; height:200px; border-radius:50%;
    background:conic-gradient({risk_color} 0deg {score*3.6:.1f}deg,#e0e0e0 {score*3.6:.1f}deg 360deg);
    display:flex; align-items:center; justify-content:center; margin:0 auto 16px; }}
  .score-inner {{ width:158px; height:158px; border-radius:50%; background:#fff;
    display:flex; flex-direction:column; align-items:center; justify-content:center; box-shadow:0 4px 12px rgba(0,0,0,.1); }}
  .score-number {{ font-size:54px; font-weight:bold; color:{risk_color}; }}
  .score-label {{ font-size:13px; color:#999; }}
  .risk-label {{ font-size:20px; font-weight:bold; color:{risk_color}; margin-top:12px; }}
  .score-table {{ width:100%; border-collapse:collapse; margin:20px 0; font-size:14px; }}
  .score-table th {{ background:#f5f5f5; padding:11px; text-align:left; border-bottom:2px solid #ddd; }}
  .score-table td {{ padding:9px 11px; border-bottom:1px solid #eee; }}
  .score-table tr:last-child td {{ border-bottom:none; font-weight:bold; background:#f9f9f9; }}
  .dimensions {{ padding:30px; }}
  .section-title {{ font-size:22px; font-weight:bold; margin-bottom:18px; color:#1a1a2e; }}
  .dim-card {{ margin-bottom:22px; border-radius:12px; padding:22px; background:#fafafa; border-left:5px solid #ddd; }}
  .dim-header {{ display:flex; justify-content:space-between; align-items:center; margin-bottom:10px; flex-wrap:wrap; gap:10px; }}
  .dim-title {{ font-size:16px; font-weight:bold; color:#1a1a2e; }}
  .dim-weight {{ color:#999; font-size:13px; margin-left:8px; }}
  .dim-score {{ font-size:26px; font-weight:bold; }}
  .dim-max {{ font-size:14px; color:#999; font-weight:normal; }}
  .dim-detail {{ font-size:13.5px; color:#555; line-height:1.8; }}
  .dim-detail p {{ margin:4px 0; }}
  .score-bar {{ height:8px; background:#e0e0e0; border-radius:4px; overflow:hidden; margin:12px 0; }}
  .score-bar-fill {{ height:100%; border-radius:4px; }}
  .tweet-quote {{ background:#fff3cd; border-left:3px solid #f0ad4e; padding:6px 10px; border-radius:4px; margin:4px 0 !important; }}
  .legend {{ padding:20px 30px; background:#fffde7; border-top:1px solid #fff9c4; font-size:13px; line-height:2; }}
  .findings {{ padding:24px 30px; background:#fdf2f2; border-top:1px solid #f5c6c6; font-size:13.5px; line-height:1.9; color:#5a3a3a; }}
  .findings p {{ margin:8px 0; }}
  .tweets-wrap {{ padding:0 30px 30px; }}
  .tweets-table {{ width:100%; border-collapse:collapse; font-size:12.5px; }}
  .tweets-table th {{ background:#f5f5f5; padding:9px; text-align:left; border-bottom:2px solid #ddd; }}
  .tweets-table td {{ padding:8px 9px; border-bottom:1px solid #eee; vertical-align:top; }}
  .tweet-text {{ max-width:420px; }}
  .footer {{ padding:18px; text-align:center; font-size:12px; color:#999; border-top:1px solid #eee; }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>X 账号风险评估报告</h1>
    <p>{esc(handle)} · {esc(name)}</p>
    <p>评估日期：{esc((meta.get('evaluated_at') or '')[:10])} ｜ 引擎：v4.3（10 维度） ｜ 数据源：{esc(meta.get('data_source') or '')}</p>
  </div>
    <div class="score-section">
    <div class="score-circle"><div class="score-inner">
      <div class="score-number">{score}</div>
      <div class="score-label">/ 100 分</div>
    </div></div>
    <div class="risk-label">{risk_emoji} {level_cn}</div>
    <p style="margin-top:10px;font-size:14px;color:#666;">
      粉丝 {meta.get('followers', '?')} ｜ 关注 {meta.get('following', '?')} ｜ 分析推文 {meta.get('tweets_analyzed', len(tweets))} 条
    </p>
    <div style="margin-top:22px;">
      <h3 style="margin-bottom:12px;">📊 各维度得分汇总（分数越高风险越大）</h3>
      <table class="score-table">
        <tr><th>维度</th><th>满分</th><th>得分</th><th>满分</th><th>得分率</th></tr>
        {score_rows}
      </table>
      <p style="font-size:13px;color:#555;background:#e8f5e9;padding:12px;border-radius:8px;text-align:left;">
        <strong>✅ 归一化验证：</strong>总分 {dim_total}/{total_max} → 归一化 {score}/100
        （{esc(handle)} 维度得分之和为 {dim_total}，按满分 {total_max} 折算）<br>
        <strong>⚠️ 等级阈值：</strong>≥60 高风险 / 30–59 中风险 / &lt;30 低风险
      </p>
    </div>
  </div>
  {findings_html}
  <div class="dimensions">
    <h2 class="section-title">📋 10 维度详细评分（含扣分标准）</h2>
    {cards}
  </div>
  <div class="tweets-wrap">
    <h2 class="section-title">📄 推文样本（前 {min(25, len(tweets))} 条）</h2>
    <table class="tweets-table">
      <tr><th>日期</th><th>内容</th><th>赞</th><th>转</th><th>阅读</th><th>媒体</th><th>敏感标记</th></tr>
      {tweet_rows}
    </table>
  </div>
  <div class="legend">
    <strong>💡 数据覆盖说明：</strong><br>{coverage}<br>
    <strong>💡 评分规则：</strong>总分 = 各维度风险分之和（分数越高风险越大），归一化到 0-100；负分 = 信任加分。
  </div>
  <div class="footer">
    X 账号风险监控系统 v4.3（10 维度）｜ 数据来源：登录态 DOM 时间线 + X embed + fxTwitter ｜ 仅用于合规研究
  </div>
</div>
</body>
</html>"""
    return html_doc


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python gen_report_v4.py <risk_json> [output.html]")
        sys.exit(2)
    data = json.load(open(sys.argv[1], encoding="utf-8"))
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(
        os.path.dirname(sys.argv[1]), "zixuanmiao_risk_report.html"
    )
    html_out = gen_report(data)
    with open(out, "w", encoding="utf-8") as f:
        f.write(html_out)
    print("Report written to", out, "| bytes:", len(html_out), "| score:", data["score"], data["level"])
