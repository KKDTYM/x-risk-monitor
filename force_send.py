#!/usr/bin/env python3
import os
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header

# 加载配置
with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

smtp = config.get("smtp_settings", {})
if not smtp.get("enabled"):
    print("Error: SMTP not enabled in config")
    exit(1)

sender = smtp.get("sender_email")
password = smtp.get("smtp_password")
server_host = smtp.get("smtp_server")
port = smtp.get("smtp_port")

# 需要强制发送的正式用户
targets = [
    {
        "username": "dangao0709",
        "email": "1525807496@qq.com",
        "report_file": "dangao0709_rectification_v5.html",
        "score": 30,
        "level": "中等"
    },
    {
        "username": "kaixintangtang",
        "email": "1468266264@qq.com",
        "report_file": "kaixintangtang_rectification_v5.html",
        "score": 6,
        "level": "低"
    }
]

for t in targets:
    username = t["username"]
    recipient = t["email"]
    html_file = t["report_file"]
    
    if not os.path.exists(html_file):
        print(f"Error: Report file {html_file} not found for @{username}")
        continue

    # 读取 HTML 报告内容
    with open(html_file, "r", encoding="utf-8") as f:
        html_content = f.read()

    # 构造邮件
    message = MIMEMultipart("alternative")
    message["From"] = sender
    message["To"] = recipient
    message["Subject"] = Header(f"【紧急自查】您的 X 账号 @{username} 违规风险自查报告 (评级: {t['level']}风险)", "utf-8")

    # 1. 纯文本降级版本
    text_content = f"""【X 平台账号违规风险自查提醒】
账号名: @{username}
风险等级: 【{t['level']}风险】
风险评分: {t['score']}/100

报告已生成，详情请查看邮件内嵌 HTML 或浏览器打开附件。
*此通知为自动化风险分析系统提醒，请尽快自查。*"""
    
    part1 = MIMEText(text_content, "plain", "utf-8")
    part2 = MIMEText(html_content, "html", "utf-8")
    
    message.attach(part1)
    message.attach(part2)

    try:
        print(f"Sending email to {recipient} (@{username})...")
        with smtplib.SMTP_SSL(server_host, port, timeout=15) as server:
            server.login(sender, password)
            server.sendmail(sender, [recipient], message.as_string())
        print(f"Success: Email sent to {recipient} for @{username}!")
    except Exception as e:
        print(f"Failed to send email for @{username}: {e}")

print("All tasks finished.")
