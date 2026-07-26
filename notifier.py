#!/usr/bin/env python3
"""
通知模块：可自动向目标用户的QQ邮箱发送风险检测结果，并保留本地文本副本以备查阅
"""
import os
import json
import smtplib
import logging
from datetime import datetime
from email.mime.text import MIMEText
from email.header import Header

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

class XNotifier:
    def __init__(self, config_path="config.json"):
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = json.load(f)
        self.smtp_settings = self.config.get("smtp_settings", {})
        self.accounts = self.config.get("accounts", [])
        self.output_dir = "data/notifications"
        os.makedirs(self.output_dir, exist_ok=True)

    def generate_and_send_notifications(self, date_str=None, risk_data_map=None):
        if not date_str:
            date_str = datetime.now().strftime("%Y-%m-%d")

        if risk_data_map is None:
            risk_data_map = {}

        results = {}
        for acc in self.accounts:
            username = acc["username"]
            email = acc.get("email")
            qq = acc.get("qq")
            
            # 读取该账号的采集结果
            data_file = f"data/account_data/{username}/{date_str}.json"
            if not os.path.exists(data_file):
                logger.warning(f"No collected data for @{username} on {date_str}, skipping.")
                continue

            with open(data_file, "r", encoding="utf-8") as f:
                scraped_data = json.load(f)

            # 获取敏感推文
            tweets = scraped_data.get("recent_tweets", [])
            sensitive_tweets = []
            for t in tweets:
                # 判断条件：推特敏感标记或含有高风险关键词
                if t.get("possibly_sensitive"):
                    sensitive_tweets.append(t)
                else:
                    # 敏感词匹配
                    text = t.get("text", "")
                    keywords = ["男娘", "ts", "femboy", "cd", "雌堕", "裙子", "伪女", "女装", "骚货", "烧杯", "丝袜", "玉足", "美腿", "露", "门槛", "约", "视频", "照片", "福利", "私发"]
                    if any(kw in text.lower() for kw in keywords):
                        sensitive_tweets.append(t)

            # 获取该账号的风险评分数据
            risk_data = risk_data_map.get(username, {})

            # 生产个性化通知草稿（含风险评分摘要）
            content = self._build_notification_text(username, acc.get("display_name"), sensitive_tweets, len(tweets), risk_data)
            
            # 保存到本地副本
            local_path = os.path.join(self.output_dir, f"{username}_notify.txt")
            with open(local_path, "w", encoding="utf-8") as f:
                f.write(content)
            logger.info(f"Notification draft saved locally: {local_path}")
            
            results[username] = {
                "email": email,
                "qq": qq,
                "draft_path": local_path,
                "sensitive_count": len(sensitive_tweets),
                "sent": False
            }

            # 判断风险等级，只有高风险（≥60分）才发送邮件通知
            risk_data = risk_data_map.get(username, {})
            risk_score = risk_data.get("score", 0) if isinstance(risk_data, dict) else 0
            
            should_send_email = (
                self.smtp_settings.get("enabled") 
                and risk_score >= 60
            )
            
            if should_send_email:
                try:
                    self._send_email(email, username, content)
                    results[username]["sent"] = True
                    logger.info(f"Email sent successfully to {email} for @{username} (风险评分: {risk_score}/100)")
                except Exception as e:
                    logger.error(f"Failed to send email to {email} for @{username}: {e}")
                    results[username]["error"] = str(e)
            else:
                if self.smtp_settings.get("enabled"):
                    level_name = "高" if risk_score >= 60 else "中/低"
                    logger.info(f"风险评分 {risk_score}/100（{level_name}风险），仅保存本地草稿，不发送邮件。")
                else:
                    logger.info(f"SMTP not enabled. Draft ready for manual copy.")

        return results

    def _build_notification_text(self, username, display_name, sensitive_tweets, total_count, risk_data=None):
        """生成发送个人的提醒文案（包含风险评分摘要）"""
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        # 从风险评分数据提取信息
        risk_score = 0
        risk_level = "低"
        risk_details = []
        recommendation = ""
        
        if risk_data and isinstance(risk_data, dict):
            risk_score = risk_data.get("score", 0)
            level_map = {"high": "高", "medium": "中", "low": "低"}
            risk_level = level_map.get(risk_data.get("level", "low"), "低")
            risk_details = risk_data.get("details", [])
            recommendation = risk_data.get("recommendation", "")

        # 基础风险评估
        warning_msg = ""
        if risk_score >= 60:
            risk_level = "高"
            warning_msg = (
                f"🔴 风险评分: {risk_score}/100（高风险）\n"
                f"系统检测到账号有较明显的违规发帖行为（含敏感图文、色情暗示或成人推广）。\n"
                f"根据 X 平台 2026 最新规则，此类推文会被置为敏感（Only Visible to Adult Settings）或降权。\n"
                f"如被批量举报或判定为色情引流，账号将面临直接【永久冻结 / Suspended】风险。\n"
                f"强烈建议立即自查并清理以下敏感/违规推文，规避封号风险。"
            )
        elif risk_score >= 30:
            risk_level = "中"
            warning_msg = (
                f"🟡 风险评分: {risk_score}/100（中等风险）\n"
                f"系统检测到账号有一定违规发帖行为（含部分敏感图文、高转发比例或较低原创度）。\n"
                f"建议定期自查，适当提升原创比例，对敏感内容添加 NSFW 标记。"
            )
        else:
            risk_level = "低"
            warning_msg = (
                f"🟢 风险评分: {risk_score}/100（低风险）\n"
                f"账号状态良好，发帖内容合规，建议继续保持健康发帖习惯。"
            )

        text = f"【X 平台账号违规风险自查提醒】\n"
        text += f"账号名: @{username} ({display_name})\n"
        text += f"检测时间: {now_str}\n"
        text += f"本次分析样本: {total_count} 条最近帖子（含转发）\n"
        text += f"风险等级: 【{risk_level}】\n"
        text += f"风险评分: {risk_score}/100\n\n"

        if risk_details:
            text += f"【风险详情】:\n"
            for detail in risk_details:
                text += f"  • {detail}\n"
            text += f"\n"

        if recommendation:
            text += f"【建议】:\n{recommendation}\n\n"

        text += f"--------------------------------------------------\n"
        text += f"{warning_msg}\n"
        text += f"--------------------------------------------------\n\n"

        if sensitive_tweets:
            text += f"【触发风险警告的帖子明细（共 {len(sensitive_tweets)} 条）】:\n\n"
            for i, t in enumerate(sensitive_tweets):
                tag = "【转发】" if t.get("is_retweet") else "【原创】"
                author = t.get("original_author", "")
                author_str = f" (转自 @{author})" if author and author != username else ""
                text += f"{i+1}. {tag}{author_str}:\n"
                text += f"   内容: {t.get('text', '').strip()}\n"
                text += f"   链接: {t.get('url', '')}\n"
                if t.get("possibly_sensitive"):
                    text += f"   特征: X平台官方已标记此条为[敏感/NSFW内容]\n"
                text += f"-----------------------------------------\n"
        else:
            text += f"未发现明显的违规帖文。\n"
            
        text += f"\n*注：此通知为自动化风险分析系统提醒，请尽快核实自查。*"
        return text

    def _send_email(self, recipient_email, username, text_content):
        """SMTP SSL 发送邮件"""
        sender = self.smtp_settings.get("sender_email")
        password = self.smtp_settings.get("smtp_password")
        server_host = self.smtp_settings.get("smtp_server")
        port = self.smtp_settings.get("smtp_port")

        message = MIMEText(text_content, "plain", "utf-8")
        message["From"] = sender
        message["To"] = recipient_email
        message["Subject"] = Header(f"【紧急自查】您的 X 账号 @{username} 违规风险提醒", "utf-8")

        # QQ 邮箱一般使用 SSL 465 端口
        with smtplib.SMTP_SSL(server_host, port, timeout=15) as server:
            server.login(sender, password)
            server.sendmail(sender, [recipient_email], message.as_string())

if __name__ == "__main__":
    notifier = XNotifier()
    res = notifier.generate_and_send_notifications()
    print("通知处理结果：", json.dumps(res, indent=2, ensure_ascii=False))
