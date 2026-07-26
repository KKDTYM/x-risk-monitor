#!/usr/bin/env python3
"""
HTML 报告生成器：生成可读的风险评估报告
"""
import os
import re
import json
import datetime


class ReportGenerator:
    def __init__(self, config):
        self.report_dir = config["output"]["report_dir"]
        os.makedirs(self.report_dir, exist_ok=True)

    def generate_report(self, date_str, account_results):
        """生成完整的 HTML 风险报告"""
        html = self._build_html(date_str, account_results)
        filepath = os.path.join(self.report_dir, f"x_risk_report_{date_str}.html")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html)
        return filepath

    def _build_html(self, date_str, results):
        """构建 HTML 报告内容"""
        level_colors = {
            "low": "#22c55e",
            "medium": "#f59e0b",
            "high": "#ef4444"
        }
        level_names = {
            "low": "低",
            "medium": "中",
            "high": "高"
        }

        # 概览部分
        overview_html = ""
        for username, result in results.items():
            level = result["assessment"]["level"]
            score = result["assessment"]["score"]
            color = level_colors.get(level, "#6b7280")
            name = level_names.get(level, "未知")
            overview_html += f"""
            <div class="overview-card" style="border-left: 4px solid {color};">
                <h3 style="margin: 0 0 8px 0;">@{username}</h3>
                <div class="score-display" style="color: {color}; font-size: 2em; font-weight: bold;">
                    {score}/100
                </div>
                <div class="level-badge" style="background: {color}; color: white; padding: 4px 12px; border-radius: 12px; display: inline-block; margin-top: 8px;">
                    风险等级：{name}
                </div>
            </div>
            """

        # 详细报告部分
        detail_html = ""
        for username, result in results.items():
            assessment = result["assessment"]
            score = assessment["score"]
            level = assessment["level"]
            details = assessment.get("details", [])
            recommendation = assessment.get("recommendation", "")
            raw = result["raw"]

            # 基本信息 - 兼容新旧数据结构
            profile = raw.get("profile", {})
            if isinstance(profile, dict):
                followers = profile.get("followers_count", "N/A")
                following = profile.get("following_count", "N/A")
                tweet_count = profile.get("tweet_count", "N/A")
                bio = profile.get("description", "")
                registered_date = profile.get("created_at", "")
            else:
                followers = raw.get("followers", "N/A")
                following = raw.get("following", "N/A")
                tweet_count = raw.get("tweet_count", "N/A")
                bio = raw.get("bio", "")
                registered_date = raw.get("registered_date", "")
                
            account_status = raw.get("account_status", "unknown")
            is_sensitive = raw.get("is_sensitive", False)

            # 兼容新旧 account_status 格式
            if isinstance(account_status, dict):
                if account_status.get("is_suspended"):
                    status_text = "冻结"
                elif account_status.get("is_protected"):
                    status_text = "私密"
                else:
                    status_text = "正常"
            else:
                status_map = {
                    "normal": "正常",
                    "restricted": "受限",
                    "locked": "锁定",
                    "suspended": "冻结",
                    "unknown": "未知"
                }
                status_text = status_map.get(account_status, account_status)

            # 最近推文列表（展示全部，违规推文带标记）
            tweets_html = ""
            recent_tweets = raw.get("recent_tweets", [])
            if recent_tweets:
                for tweet in recent_tweets:
                    flag = ""
                    style_prefix = "#e5e7eb"
                    tweet_flag = ""
                    
                    if tweet.get("is_sensitive") or tweet.get("is_nsfw"):
                        flag = " 🟡敏感" if tweet.get("is_sensitive") else " 🔴NSFW"
                        style_prefix = "#f59e0b" if tweet.get("is_sensitive") else "#ef4444"
                    
                    # 检查是否是转发
                    is_retweet = tweet.get("is_retweet", False)
                    text = tweet.get("text", "")
                    
                    if is_retweet:
                        tweet_flag = " 🔁转发"
                        style_prefix = "#3b82f6"  # 蓝色标记转发
                    
                    # 清理 HTML 标签
                    clean_text = re.sub(r'<[^>]+>', '', text) if isinstance(text, str) else str(text)
                    clean_text = clean_text[:300]  # 限制长度
                    
                    tweets_html += f"""
                    <div class="tweet-item" style="padding: 12px; margin: 8px 0; background: #f9fafb; border-radius: 8px; border-left: 3px solid {style_prefix};">
                        <div style="font-size: 0.85em; color: #6b7280; margin-bottom: 4px;">
                            {tweet.get('date', 'N/A') or tweet.get('created_at', '')}{flag}{tweet_flag}
                        </div>
                        <div style="margin-bottom: 4px; line-height: 1.5;">{self._escape_html(clean_text)}</div>
                        <div style="font-size: 0.8em; color: #9ca3af;">
                            {tweet.get('url', '') and f'<a href="{tweet["url"]}" target="_blank" style="color: #3b82f6;">查看推文</a>' or ''}
                        </div>
                    </div>
                    """
            else:
                tweets_html = "<p style='color: #9ca3af;'>未获取到推文数据</p>"

            # 风险详情
            details_html = ""
            if details:
                for detail in details:
                    details_html += f"<li style='padding: 4px 0;'>{self._escape_html(detail)}</li>"
            else:
                details_html = "<li style='color: #22c55e;'>✅ 无明显风险</li>"

            detail_html += f"""
            <div class="account-section" style="margin: 32px 0; padding: 24px; background: white; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                <h2 style="margin: 0 0 16px 0; padding-bottom: 12px; border-bottom: 2px solid #e5e7eb;">
                    @{username}
                </h2>

                <div class="info-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 24px;">
                    <div class="info-card" style="padding: 16px; background: #f9fafb; border-radius: 8px;">
                        <div style="font-size: 0.85em; color: #6b7280;">粉丝数</div>
                        <div style="font-size: 1.5em; font-weight: bold; color: #111827;">{followers}</div>
                    </div>
                    <div class="info-card" style="padding: 16px; background: #f9fafb; border-radius: 8px;">
                        <div style="font-size: 0.85em; color: #6b7280;">关注数</div>
                        <div style="font-size: 1.5em; font-weight: bold; color: #111827;">{following}</div>
                    </div>
                    <div class="info-card" style="padding: 16px; background: #f9fafb; border-radius: 8px;">
                        <div style="font-size: 0.85em; color: #6b7280;">推文数</div>
                        <div style="font-size: 1.5em; font-weight: bold; color: #111827;">{tweet_count}</div>
                    </div>
                    <div class="info-card" style="padding: 16px; background: #f9fafb; border-radius: 8px;">
                        <div style="font-size: 0.85em; color: #6b7280;">账号状态</div>
                        <div style="font-size: 1.2em; font-weight: bold; color: {'#22c55e' if account_status == 'normal' else '#ef4444'};">{status_text}</div>
                    </div>
                </div>

                <div style="margin-bottom: 24px;">
                    <h3 style="margin: 0 0 12px 0; font-size: 1.1em;">风险等级</h3>
                    <div style="display: flex; align-items: center; gap: 16px;">
                        <div style="font-size: 2.5em; font-weight: bold; color: {level_colors.get(level, '#6b7280')};">{score}/100</div>
                        <div style="background: {level_colors.get(level, '#6b7280')}; color: white; padding: 8px 20px; border-radius: 16px; font-size: 1.1em; font-weight: bold;">
                            风险等级：{level_names.get(level, '未知')}
                        </div>
                    </div>
                </div>

                {'<div style="margin-bottom: 24px;"><h3 style="margin: 0 0 12px 0;">简介</h3><p>' + bio + '</p></div>' if bio else ''}

                <div style="margin-bottom: 24px;">
                    <h3 style="margin: 0 0 12px 0; font-size: 1.1em;">风险详情</h3>
                    <ul style="list-style: none; padding: 0;">
                        {details_html}
                    </ul>
                </div>

                <div style="margin-bottom: 24px; padding: 16px; background: #fef3c7; border-radius: 8px; border-left: 4px solid #f59e0b;">
                    <strong>建议：</strong>{self._escape_html(recommendation)}
                </div>

                <div>
                    <h3 style="margin: 0 0 12px 0; font-size: 1.1em;">最近推文（{len(recent_tweets)} 条）</h3>
                    {tweets_html}
                </div>
            </div>
            """

        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>X账号风险监控报告 - {date_str}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: #f3f4f6;
            color: #111827;
            line-height: 1.6;
            padding: 24px;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .header {{
            background: white;
            padding: 32px;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            margin-bottom: 32px;
            text-align: center;
        }}
        .header h1 {{ font-size: 2em; margin-bottom: 8px; color: #111827; }}
        .header .date {{ color: #6b7280; font-size: 1.1em; }}
        .overview-section {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 20px;
            margin-bottom: 32px;
        }}
        .overview-card {{
            background: white;
            padding: 24px;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        .tweet-item {{ }}
        .account-section {{ }}
        .info-grid {{ }}
        .info-card {{ }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🛡️ X 账号违规风险监控报告</h1>
            <div class="date">报告日期：{date_str}</div>
        </div>

        <div class="overview-section">
            {overview_html}
        </div>

        {detail_html}

        <div style="text-align: center; padding: 24px; color: #6b7280; font-size: 0.9em;">
            <p>报告由 X 账号风险监控系统自动生成 | 数据来源：x.com</p>
        </div>
    </div>
</body>
</html>"""
        return html

    def _escape_html(self, text):
        """转义 HTML 特殊字符"""
        if not text:
            return ""
        text = text.replace("&", "&amp;")
        text = text.replace("<", "&lt;")
        text = text.replace(">", "&gt;")
        text = text.replace('"', "&quot;")
        text = text.replace("'", "&#39;")
        return text
