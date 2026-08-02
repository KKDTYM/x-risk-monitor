#!/usr/bin/env python3
"""
数据持久化模块：JSON 存储历史采集数据
"""
import os
import json
import datetime
import glob


class DataStore:
    def __init__(self, config):
        self.raw_dir = config["output"]["raw_data_dir"]
        self.report_dir = config["output"]["report_dir"]
        os.makedirs(self.raw_dir, exist_ok=True)
        os.makedirs(self.report_dir, exist_ok=True)

    def _account_dir(self, username):
        """获取账号数据目录"""
        account_dir = os.path.join(self.raw_dir, username)
        os.makedirs(account_dir, exist_ok=True)
        return account_dir

    def save_daily_data(self, username, date_str, data):
        """保存每日采集的原始数据"""
        account_dir = self._account_dir(username)
        filepath = os.path.join(account_dir, f"{date_str}.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return filepath

    def load_daily_data(self, username, date_str):
        """加载指定日期的原始数据"""
        account_dir = self._account_dir(username)
        filepath = os.path.join(account_dir, f"{date_str}.json")
        if not os.path.exists(filepath):
            return None
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)

    def load_historical_data(self, username, days=30):
        """加载历史数据用于趋势分析"""
        account_dir = self._account_dir(username)
        pattern = os.path.join(account_dir, "*.json")
        files = glob.glob(pattern)
        # 按日期排序，取最近 days 天
        dates = []
        for f in files:
            basename = os.path.basename(f).replace(".json", "")
            try:
                date_obj = datetime.datetime.strptime(basename, "%Y-%m-%d").date()
                cutoff = datetime.date.today() - datetime.timedelta(days=days)
                if date_obj >= cutoff:
                    dates.append((date_obj, f))
            except ValueError:
                continue
        # 按日期排序
        dates.sort(key=lambda x: x[0], reverse=True)
        historical = []
        for date_obj, filepath in dates:
            with open(filepath, "r", encoding="utf-8") as f:
                historical.append({
                    "date": date_obj.isoformat(),
                    "data": json.load(f)
                })
        return historical

    def get_follower_trend(self, username, days=30):
        """获取粉丝数趋势（用于报告中的图表数据）"""
        historical = self.load_historical_data(username, days)
        trend = []
        for item in historical:
            data = item["data"]
            followers = data.get("followers")
            if followers is not None:
                trend.append({
                    "date": item["date"],
                    "followers": followers
                })
        return trend

    def save_report(self, date_str, report_html):
        """保存生成的 HTML 报告"""
        filename = f"x_risk_report_{date_str}.html"
        filepath = os.path.join(self.report_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(report_html)
        return filepath

    def list_reports(self):
        """列出所有已生成的报告"""
        pattern = os.path.join(self.report_dir, "*.html")
        files = glob.glob(pattern)
        reports = []
        for f in files:
            basename = os.path.basename(f)
            reports.append({
                "filename": basename,
                "filepath": f,
                "size": os.path.getsize(f)
            })
        reports.sort(key=lambda x: x["filename"], reverse=True)
        return reports
