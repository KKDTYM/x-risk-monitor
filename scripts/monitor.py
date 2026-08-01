#!/usr/bin/env python3
"""
X 账号违规风险监控系统
每日扫描指定 X 账号，输出风险评估报告

使用方式：
    python monitor.py                    # 使用默认配置
    python monitor.py --config path.json # 指定配置文件
"""
import os
import sys
import json
import datetime
import asyncio

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scraper import XScraper
from risk_engine import RiskEngine
from data_store import DataStore
from report_generator import ReportGenerator


async def monitor_account(username, scraper, config, data_store, risk_engine):
    """监控单个账号"""
    print(f"  正在采集 @{username} ...")

    # 采集数据（复用同一个 scraper 实例）
    raw_data = await scraper.scrape_account(username)

    # 加载历史数据
    historical = data_store.load_historical_data(username, days=30)

    # 保存原始数据
    date_str = datetime.date.today().isoformat()
    data_store.save_daily_data(username, date_str, raw_data)

    # 评估风险
    assessment = risk_engine.assess_account(raw_data, historical)

    return {
        "raw": raw_data,
        "assessment": assessment,
        "date": date_str
    }


async def main_async():
    """主入口（async 版本）"""
    # 解析参数
    config_path = "config.json"
    if "--config" in sys.argv:
        idx = sys.argv.index("--config")
        if idx + 1 < len(sys.argv):
            config_path = sys.argv[idx + 1]

    # 加载配置
    if not os.path.exists(config_path):
        print(f"错误：配置文件 {config_path} 不存在")
        sys.exit(1)

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    date_str = datetime.date.today().isoformat()
    print(f"\n{'='*60}")
    print(f"  X 账号违规风险监控")
    print(f"  日期：{date_str}")
    print(f"{'='*60}\n")

    # 初始化组件
    data_store = DataStore(config)
    risk_engine = RiskEngine(config)
    report_gen = ReportGenerator(config)

    # 启动浏览器（复用同一个实例）
    scraper = await XScraper(config).start()

    try:
        # 监控每个账号（复用浏览器实例）
        results = {}
        for account in config["accounts"]:
            username = account["username"]
            try:
                result = await monitor_account(username, scraper, config, data_store, risk_engine)
                results[username] = result
            except Exception as e:
                print(f"  错误：@{username} 采集失败 - {e}")
                results[username] = {
                    "raw": {"username": username, "error": str(e)},
                    "assessment": {
                        "score": 30,
                        "level": "medium",
                        "details": [f"采集失败：{e}"],
                        "recommendation": "检查网络连接或账号是否存在"
                    },
                    "date": date_str
                }

        # 关闭浏览器
        await scraper.stop()
    except Exception as e:
        print(f"  浏览器关闭错误：{e}")
        await scraper.stop()

    # 生成报告
    report_path = report_gen.generate_report(date_str, results)
    print(f"\n{'='*60}")
    print(f"  报告已生成：{report_path}")
    print(f"{'='*60}\n")

    # 输出概览
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


def main():
    """主入口"""
    return asyncio.run(main_async())


if __name__ == "__main__":
    main()
