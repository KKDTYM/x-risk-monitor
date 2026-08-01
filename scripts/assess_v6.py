#!/usr/bin/env python3
"""
v6 评估脚本：用 risk_engine v4 标准重新评估所有监控账号
"""
import json
import sys
import os
import datetime

# 添加项目路径
project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_dir)

from risk_engine import RiskEngine

# 监控账号配置
MONITORED_ACCOUNTS = [
    {"handle": "dangao0709", "name": "小蛋糕", "is_formal": True},
    {"handle": "kaixintangtang", "name": "糖姐不吃糖", "is_formal": True},
]


def load_tweets(handle):
    """加载推文数据"""
    tweets_path = os.path.join(project_dir, "data", f"{handle}_tweets.json")
    if not os.path.exists(tweets_path):
        print(f"❌ 推文文件不存在: {tweets_path}")
        return None

    with open(tweets_path, "r", encoding="utf-8") as f:
        tweets = json.load(f)

    print(f"  📄 加载 {handle} 推文: {len(tweets)} 条")
    return tweets


def build_raw_data(handle, tweets):
    """
    构建 risk_engine 所需的 raw_data 格式
    """
    # 基础 profile
    profile = {
        "username": handle,
        "name": handle,
        "followers_count": 0,
        "following_count": 0,
    }

    # 统计转发数
    retweet_count = sum(1 for t in tweets if t.get("is_retweet"))
    original_count = len(tweets) - retweet_count
    retweet_ratio = retweet_count / len(tweets) if tweets else 0

    # account_status — 模拟（因为抓取时没有完整账户信息）
    account_status = {
        "is_suspended": False,
        "is_frozen": False,
        "acc_status": "unknown",  # 无法从公开数据判断
        "premium_type": "none",
        "ip_type": "unknown",
        "search_visibility": True,
        "report_count": 0,
        "has_warning": False,
        "violation_count": 0,
        "needs_verification": False,
        "suspicious_login": False,
        "dirty_device": False,
        "shared_ip": False,
    }

    # 分析推文统计信息
    adult_keywords = [
        "小穴", "肉棒", "鸡巴", "淫", "精液", "自慰", "高潮", "蜜穴", "屁穴",
        "男娘", "伪娘", "男の娘", "mtf", "ftm", "药娘", "cd", "crossdress",
        "femboy", "ts", "乳胶", "latex", "胶衣", "女仆", "假发", "cosplay",
        "spider", "金臀", "欲魅", "Gothic", "蕾丝", "丝袜", "黑丝", "白丝",
        "美腿", "玉足", "福利", "私拍", "私房", "写真", "性感", "裸体",
        "nsfw", "18+", "adult", "涩涩", "调教", "拘束", "sm", "露出",
        "颜射", "足交", "手淫", "飞机杯", "吃药", "事后",
        "援交", "约炮", "yp", "娼年",
        "插穴", "口交", "肛交", "阴道", "阴茎", "阴蒂", "大胸", "巨乳",
        "裸照", "果照", "走光", "姿势", "体位", "变态",
        "操", "干", "婊子", "骚", "操粉",
        "yp", "草粉", "上床"
    ]

    adult_tweets = []
    for t in tweets:
        text_lower = str(t.get("text", "")).lower()
        raw_str = str(t.get("raw", "") + " " + t.get("retweet_text", ""))
        has_adult = any(kw in text_lower for kw in adult_keywords)
        has_media = "https://" in raw_str or "t.co/" in raw_str
        if has_adult and has_media:
            adult_tweets.append(t)

    # 分析时间分布
    dates = []
    for t in tweets:
        if t.get("datetime"):
            try:
                dt = datetime.datetime.fromisoformat(t["datetime"].replace("Z", "+00:00"))
                dates.append(dt)
            except:
                pass

    # 分析回复
    reply_count = sum(1 for t in tweets if t.get("is_reply"))

    # 统计关注/粉丝比（估算）
    if handle == "dangao0709":
        # 基于历史数据估算
        profile["followers_count"] = 12000
        profile["following_count"] = 850
    elif handle == "kaixintangtang":
        profile["followers_count"] = 3200
        profile["following_count"] = 420

    raw_data = {
        "recent_tweets": tweets,
        "profile": profile,
        "account_status": account_status,
        "tweet_stats": {
            "total": len(tweets),
            "original": original_count,
            "retweet": retweet_count,
            "retweet_ratio": retweet_ratio,
            "adult_tweets": len(adult_tweets),
            "reply_count": reply_count,
            "unique_dates": len(set(d.strftime("%Y-%m-%d") for d in dates)) if dates else 0,
        }
    }

    return raw_data


def assess(handle, tweets):
    """评估单个账号"""
    print(f"\n{'='*60}")
    print(f"🔍 评估账号: @{handle}")
    print(f"{'='*60}")

    raw_data = build_raw_data(handle, tweets)
    engine = RiskEngine({})

    # v6 用 v4 引擎，传入 tweets 作为 raw_data
    result = engine.assess_account(raw_data, [])

    return result


def gen_v6_report(result, handle, tweets, raw_data):
    """生成 v6 HTML 报告"""
    # 统计数据
    stats = raw_data.get("tweet_stats", {})
    total = stats.get("total", 0)
    original = stats.get("original", 0)
    retweet = stats.get("retweet", 0)
    retweet_ratio = stats.get("retweet_ratio", 0)
    adult_count = stats.get("adult_tweets", 0)
    reply_count = stats.get("reply_count", 0)

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>@{handle} — X平台风险评分 v6</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif; background: #f5f5f5; color: #333; padding: 20px; }}
.container {{ max-width: 900px; margin: 0 auto; }}
header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 16px; margin-bottom: 24px; }}
header h1 {{ font-size: 28px; margin-bottom: 8px; }}
header .subtitle {{ opacity: 0.9; font-size: 14px; }}
.score-card {{ background: white; border-radius: 16px; padding: 30px; margin-bottom: 24px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); text-align: center; }}
.score-circle {{ width: 150px; height: 150px; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 16px; font-size: 48px; font-weight: bold; color: white; }}
.score-high {{ background: linear-gradient(135deg, #e74c3c, #c0392b); }}
.score-medium {{ background: linear-gradient(135deg, #f39c12, #e67e22); }}
.score-low {{ background: linear-gradient(135deg, #2ecc71, #27ae60); }}
.level-badge {{ display: inline-block; padding: 8px 24px; border-radius: 20px; font-size: 16px; font-weight: bold; }}
.level-high {{ background: #fde8e8; color: #e74c3c; }}
.level-medium {{ background: #fef3e2; color: #f39c12; }}
.level-low {{ background: #e8f5e9; color: #2ecc71; }}
.dimension-card {{ background: white; border-radius: 12px; padding: 20px; margin-bottom: 16px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); }}
.dimension-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }}
.dimension-name {{ font-weight: bold; font-size: 16px; }}
.dimension-score {{ font-weight: bold; font-size: 20px; }}
.dimension-bar {{ height: 8px; background: #eee; border-radius: 4px; overflow: hidden; margin-bottom: 12px; }}
.dimension-fill {{ height: 100%; border-radius: 4px; transition: width 0.5s; }}
.fill-high {{ background: linear-gradient(90deg, #e74c3c, #c0392b); }}
.fill-medium {{ background: linear-gradient(90deg, #f39c12, #e67e22); }}
.fill-low {{ background: linear-gradient(90deg, #2ecc71, #27ae60); }}
.issues {{ list-style: none; padding: 0; }}
.issues li {{ padding: 6px 0; font-size: 14px; border-bottom: 1px solid #f0f0f0; }}
.issues li:last-child {{ border-bottom: none; }}
.issues li::before {{ margin-right: 8px; }}
.stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; margin-bottom: 24px; }}
.stat-card {{ background: white; border-radius: 12px; padding: 16px; text-align: center; box-shadow: 0 2px 8px rgba(0,0,0,0.05); }}
.stat-value {{ font-size: 28px; font-weight: bold; color: #667eea; }}
.stat-label {{ font-size: 12px; color: #999; margin-top: 4px; }}
.recommendation {{ background: #fff3e0; border-left: 4px solid #f39c12; padding: 16px; border-radius: 0 12px 12px 0; margin-bottom: 24px; }}
footer {{ text-align: center; padding: 20px; color: #999; font-size: 12px; }}
</style>
</head>
<body>
<div class="container">
<header>
<h1>🔍 @{handle} 风险评估报告 v6</h1>
<div class="subtitle">基于 X 平台 2026 最新规则 | 9 维度风险评分引擎</div>
</header>

<div class="stats-grid">
<div class="stat-card">
<div class="stat-value">{total}</div>
<div class="stat-label">分析推文数</div>
</div>
<div class="stat-card">
<div class="stat-value">{original}</div>
<div class="stat-label">原创推文</div>
</div>
<div class="stat-card">
<div class="stat-value">{retweet}</div>
<div class="stat-label">转贴推文</div>
</div>
<div class="stat-card">
<div class="stat-value">{retweet_ratio:.0%}</div>
<div class="stat-label">转贴占比</div>
</div>
<div class="stat-card">
<div class="stat-value">{adult_count}</div>
<div class="stat-label">成人内容</div>
</div>
<div class="stat-card">
<div class="stat-value">{reply_count}</div>
<div class="stat-label">回复数</div>
</div>
</div>

<div class="score-card">
<div class="score-circle {'score-high' if result['score'] >= 60 else 'score-medium' if result['score'] >= 30 else 'score-low'}">
{result['score']}
</div>
<div class="level-badge {'level-high' if result['level'] == 'high' else 'level-medium' if result['level'] == 'medium' else 'level-low'}">
{result['level'] == 'high' and '🔴 高风险' or result['level'] == 'medium' and '🟡 中等风险' or '🟢 低风险'}
</div>
</div>

"""

    # 维度卡片
    dims = result.get("dimensions", {})
    for dim_key in ["acc_program", "acc_marking", "api_reply", "ip_network", "shadowban",
                     "follow_ratio", "premium", "content_diversity", "prohibited"]:
        dim = dims.get(dim_key, {})
        risk_score = dim.get("risk_score", 0)
        max_risk = dim.get("max_risk", 0)
        issues = dim.get("issues", [])

        fill_class = "fill-high" if risk_score / max_risk > 0.6 else "fill-medium" if risk_score / max_risk > 0.3 else "fill-low"
        score_class = "score-high" if risk_score / max_risk > 0.6 else "score-medium" if risk_score / max_risk > 0.3 else "score-low"

        dim_names = {
            "acc_program": "🏷️ ACC 计划合规",
            "acc_marking": "📋 ACC 三级标记合规",
            "api_reply": "💬 API 自动回复合规",
            "ip_network": "🌐 IP/网络环境",
            "shadowban": "👻 Shadowban 状态",
            "follow_ratio": "👥 关注/粉丝比",
            "premium": "⭐ Premium 会员等级",
            "content_diversity": "📊 内容多样性",
            "prohibited": "🚫 禁止内容零触碰",
        }

        html += f"""<div class="dimension-card">
<div class="dimension-header">
<div class="dimension-name">{dim_names.get(dim_key, dim_key)}</div>
<div class="dimension-score {'score-high' if risk_score/max_risk > 0.6 else 'score-medium' if risk_score/max_risk > 0.3 else 'score-low'}">{risk_score} / {max_risk}</div>
</div>
<div class="dimension-bar"><div class="dimension-fill {fill_class}" style="width: {risk_score/max_risk*100:.0f}%"></div></div>
<ul class="issues">
"""
        for issue in issues:
            html += f"<li>{issue}</li>"
        html += "</ul></div>\n"

    # 建议
    html += f"""<div class="recommendation">
<h3>💡 评估建议</h3>
<p>{result.get('recommendation', '暂无建议')}</p>
</div>

<footer>
<p>v6 风险评估引擎 | 基于 risk_engine.py v4 | 生成时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
</footer>
</div>
</body>
</html>"""

    return html


def main():
    for account in MONITORED_ACCOUNTS:
        handle = account["handle"]
        name = account["name"]
        print(f"\n{'='*60}")
        print(f"🔍 评估: @{handle} ({name})")
        print(f"{'='*60}")

        # 加载推文
        tweets_path = os.path.join(project_dir, "data", f"{handle}_tweets.json")
        if not os.path.exists(tweets_path):
            print(f"  ❌ 推文文件不存在: {tweets_path}")
            continue

        with open(tweets_path, "r", encoding="utf-8") as f:
            tweets = json.load(f)

        print(f"  📄 加载推文: {len(tweets)} 条")

        # 统计转发
        retweet_count = sum(1 for t in tweets if t.get("is_retweet"))
        print(f"  🔄 转贴: {retweet_count} 条, 原创: {len(tweets)-retweet_count} 条")

        # 构建 raw_data
        profile = {"username": handle, "name": name, "followers_count": 12000 if handle == "dangao0709" else 3200,
                    "following_count": 850 if handle == "dangao0709" else 420}
        account_status = {
            "is_suspended": False, "is_frozen": False, "acc_status": "unknown",
            "premium_type": "none", "ip_type": "unknown", "search_visibility": True,
            "report_count": 0, "has_warning": False, "violation_count": 0,
            "needs_verification": False, "suspicious_login": False,
            "dirty_device": False, "shared_ip": False,
        }
        raw_data = {
            "recent_tweets": tweets,
            "profile": profile,
            "account_status": account_status,
        }

        # 评估
        engine = RiskEngine({})
        result = engine.assess_account(raw_data, [])

        print(f"  📊 风险分: {result['score']} ({result['level']})")

        # 输出各维度
        dims = result.get("dimensions", {})
        for dim_key in ["acc_program", "acc_marking", "api_reply", "ip_network", "shadowban",
                         "follow_ratio", "premium", "content_diversity", "prohibited"]:
            dim = dims.get(dim_key, {})
            if dim:
                print(f"    {dim_key}: {dim.get('risk_score', 0)}/{dim.get('max_risk', 0)}")

        # 生成 v6 报告
        report_html = gen_v6_report(result, handle, tweets, raw_data)
        output_path = os.path.join(project_dir, "data", f"{handle}_risk_v6.html")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(report_html)
        print(f"  📄 v6 报告已保存: {output_path}")


if __name__ == "__main__":
    main()
