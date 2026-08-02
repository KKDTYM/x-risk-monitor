"""
生成 @tutu7gen1 的 v4 风险评估报告
"""
import json
import os
from datetime import datetime
from risk_engine import RiskEngine

PROJECT_DIR = r'F:\Users\Administrator\Documents\WorkBuddy\2026-07-24-21-36-14'
DATA_DIR = f'{PROJECT_DIR}/data'

# 读取抓取数据
with open(f'{DATA_DIR}/tutu7gen1_tweets_sensitive.json', 'r', encoding='utf-8') as f:
    raw_data = json.load(f)

# 配置 v4 引擎
config = {
    'risk_thresholds': {
        'high_score': 60,
        'medium_score': 30
    }
}

# 创建引擎并评估
engine = RiskEngine(config)

# 构建原始推文列表（从样本中提取）
tweets = []
for text in raw_data.get('tweets_sample', []):
    is_retweet = '已转帖' in text or 'Reposted' in text
    tweet = {
        'text': text,
        'is_retweet': is_retweet,
        'datetime': datetime.now().isoformat(),
    }
    tweets.append(tweet)

raw_data['recent_tweets'] = tweets

result = engine.assess_account(raw_data, tweets)

print('=== v4 风险评估结果 ===')
print(f'风险分: {result["score"]}')
print(f'风险等级: {result["level"]}')
print(f'建议: {result["recommendation"]}')
print()
print('=== 9 维度详情 ===')
for key, dim in result['dimensions'].items():
    print(f'{key}: {dim["risk_score"]}/{dim["max_risk"]}')
    for issue in dim.get('issues', []):
        print(f'  - {issue}')

# 生成 HTML 报告
html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>@{raw_data['username']} 风险评估报告 v4</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            max-width: 900px;
            margin: 40px auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        .container {{
            background: white;
            border-radius: 12px;
            padding: 30px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #1da1f2;
            border-bottom: 3px solid #1da1f2;
            padding-bottom: 15px;
        }}
        .score-circle {{
            width: 150px;
            height: 150px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 20px auto;
            font-size: 48px;
            font-weight: bold;
            color: white;
        }}
        .low-risk {{ background: linear-gradient(135deg, #4caf50, #66bb6a); }}
        .medium-risk {{ background: linear-gradient(135deg, #ff9800, #ffb74d); }}
        .high-risk {{ background: linear-gradient(135deg, #f44336, #ef5350); }}
        .dimension {{
            margin: 15px 0;
            padding: 15px;
            background: #f9f9f9;
            border-radius: 8px;
            border-left: 4px solid #1da1f2;
        }}
        .dimension h3 {{
            margin: 0 0 10px 0;
            color: #333;
        }}
        .score-bar {{
            height: 20px;
            background: #e0e0e0;
            border-radius: 10px;
            overflow: hidden;
            margin: 10px 0;
        }}
        .score-fill {{
            height: 100%;
            background: linear-gradient(90deg, #4caf50, #ff9800, #f44336);
            transition: width 0.3s;
        }}
        .issue {{
            margin: 5px 0;
            padding: 8px;
            background: #fff3cd;
            border-radius: 4px;
            border-left: 3px solid #ffc107;
        }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 15px;
            margin: 20px 0;
        }}
        .stat-card {{
            background: #f0f7ff;
            padding: 15px;
            border-radius: 8px;
            text-align: center;
        }}
        .stat-value {{
            font-size: 32px;
            font-weight: bold;
            color: #1da1f2;
        }}
        .stat-label {{
            color: #666;
            margin-top: 5px;
        }}
        .tweet-sample {{
            margin: 10px 0;
            padding: 10px;
            background: #f9f9f9;
            border-radius: 6px;
            font-size: 14px;
            line-height: 1.6;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🛡️ X 平台账号风险评估报告</h1>
        
        <div class="score-circle {'low-risk' if result['score'] < 30 else 'medium-risk' if result['score'] < 60 else 'high-risk'}">
            {result['score']}
        </div>
        
        <h2 style="text-align: center; color: {'#4caf50' if result['score'] < 30 else '#ff9800' if result['score'] < 60 else '#f44336'}">
            {'🟢 低风险' if result['score'] < 30 else '🟡 中风险' if result['score'] < 60 else '🔴 高风险'}
        </h2>
        
        <div class="stats">
            <div class="stat-card">
                <div class="stat-value">@{raw_data['username']}</div>
                <div class="stat-label">账号</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{result['score']}</div>
                <div class="stat-label">风险分</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{len(tweets)}</div>
                <div class="stat-label">分析推文数</div>
            </div>
        </div>
        
        <h2>📊 9 维度评分详情</h2>
"""

for key, dim in result['dimensions'].items():
    fill_width = min(100, (dim['risk_score'] / dim['max_risk']) * 100) if dim['max_risk'] > 0 else 0
    html_content += f"""
        <div class="dimension">
            <h3>{key}: {dim['risk_score']}/{dim['max_risk']}</h3>
            <div class="score-bar">
                <div class="score-fill" style="width: {fill_width}%"></div>
            </div>
"""
    for issue in dim.get('issues', []):
        html_content += f'<div class="issue">⚠️ {issue}</div>'
    html_content += '</div>'

html_content += f"""
        <h2>📝 推文样本（前 5 条）</h2>
"""

for i, tweet in enumerate(tweets[:5], 1):
    html_content += f'<div class="tweet-sample"><strong>{i}.</strong> {tweet["text"][:200]}</div>'

html_content += f"""
        <h2>💡 评估建议</h2>
        <p>{result['recommendation']}</p>
        
        <p style="color: #999; font-size: 12px; text-align: center; margin-top: 40px;">
            评估时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 
            评估引擎: X Platform Risk Engine v4 |
            数据来源: Playwright DOM 解析（处理敏感内容警告）
        </p>
    </div>
</body>
</html>
"""

# 保存 HTML 报告
output_path = f'{DATA_DIR}/tutu7gen1_risk_v4.html'
with open(output_path, 'w', encoding='utf-8') as f:
    f.write(html_content)

print(f'\n✅ HTML 报告已保存到: {output_path}')
