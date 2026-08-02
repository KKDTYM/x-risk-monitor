#!/usr/bin/env python3
"""
X 账号违规风险监控系统 — 纯 requests 版本（零依赖）
"""
import os
import sys
import json
import datetime
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scraper_requests import XScraperRequests
from risk_engine import RiskEngine
from data_store import DataStore
from report_generator import ReportGenerator


def monitor_account(username, scraper, config, data_store, risk_engine):
    """监控单个账号"""
    print(f"  正在采集 @{username} ...")

    raw_data = scraper.scrape_account(username)

    historical = data_store.load_historical_data(username, days=30)
    data_store.save_daily_data(username, datetime.date.today().isoformat(), raw_data)
    assessment = risk_engine.assess_account(raw_data, historical)

    return {
        "raw": raw_data,
        "assessment": assessment,
        "date": datetime.date.today().isoformat(),
    }


def main():
    config_path = "config.json"
    if "--config" in sys.argv:
        idx = sys.argv.index("--config")
        if idx + 1 < len(sys.argv):
            config_path = sys.argv[idx + 1]

    if not os.path.exists(config_path):
        print(f"错误：配置文件 {config_path} 不存在")
        sys.exit(1)

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    date_str = datetime.date.today().isoformat()
    print(f"\n{'='*60}")
    print(f"  X 账号违规风险监控（纯 requests）")
    print(f"  日期：{date_str}")
    print(f"{'='*60}\n")

    data_store = DataStore(config)
    risk_engine = RiskEngine(config)
    report_gen = ReportGenerator(config)
    scraper = XScraperRequests(config)

    results = {}
    for account in config["accounts"]:
        username = account["username"]
        try:
            result = monitor_account(username, scraper, config, data_store, risk_engine)
            results[username] = result
        except Exception as e:
            print(f"  错误：@{username} 采集失败 - {e}")
            results[username] = {
                "raw": {"username": username, "error": str(e)},
                "assessment": {
                    "score": 30,
                    "level": "medium",
                    "details": [f"采集失败：{e}"],
                    "recommendation": "检查网络连接或账号是否存在",
                },
                "date": date_str,
            }

    scraper.stop()

    report_path = report_gen.generate_report(date_str, results)
    print(f"\n{'='*60}")
    print(f"  报告已生成：{report_path}")
    print(f"{'='*60}\n")

    # 触发个性化邮件/本地草稿通知
    try:
        from notifier import XNotifier
        print("=== 正在生成个性化风险自查通知 ===")
        notifier = XNotifier(config_path)
        
        # 构建风险评分数据映射，供通知使用
        risk_data_map = {}
        for username, result in results.items():
            risk_data_map[username] = result["assessment"]
        
        notify_res = notifier.generate_and_send_notifications(date_str, risk_data_map)
        for username, info in notify_res.items():
            sent_status = "已发送邮件" if info.get("sent") else "仅保存本地草稿"
            print(f"  @{username}: {sent_status} -> {info.get('draft_path')} (敏感推文数: {info.get('sensitive_count')})")
        print("===================================\n")
    except Exception as ne:
        print(f"  生成通知时出错：{ne}")

    print("=== 风险概览 ===")
    for username, result in results.items():
        assessment = result["assessment"]
        level = assessment["level"]
        score = assessment["score"]
        level_names = {"low": "低", "medium": "中", "high": "高"}
        level_name = level_names.get(level, level)
        status_icon = {"low": "🟢", "medium": "🟡", "high": "🔴"}.get(level, "⚪")
        print(f"  {status_icon} @{username}: {level_name} ({score}/100)")

    print(f"\n报告路径：{report_path}")
    print(f"完成！\n")

    return report_path


if __name__ == "__main__":
    main()
