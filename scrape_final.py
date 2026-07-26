#!/usr/bin/env python3
"""
用 Playwright + HTML meta 解析抓取 X 账号推文
"""
import subprocess
import json
import re
import sys
import os

username = sys.argv[1] if len(sys.argv) > 1 else 'sunny31059'
username = username.replace('@', '')
work_dir = 'F:\\Users\\Administrator\\Documents\\WorkBuddy\\2026-07-24-21-36-14'

print(f'=== 抓取 @{username} ===')

# Step 1: 用 Playwright 获取完整 HTML
html_file = os.path.join(work_dir, f'debug_{username}.html')
script = f"""
const fs = require('fs');
const {{ chromium }} = require('playwright');

(async () => {{
    const cookies = JSON.parse(fs.readFileSync('{work_dir.replace('\\\\', '\\\\\\\\')}/conny_cookies.json', 'utf8'));
    const browser = await chromium.launch({{
        headless: true,
        executablePath: '{work_dir.replace('\\\\', '\\\\\\\\')}\\\\playwright_chrome.exe'
    }});
    const context = await browser.newContext({{
        userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
        cookies: cookies
    }});
    const page = await context.newPage();

    await page.goto('https://x.com/{username}', {{ waitUntil: 'domcontentloaded', timeout: 30000 }});
    await page.waitForTimeout(5000);

    // 滚动加载更多内容
    for (let i = 0; i < 10; i++) {{
        await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
        await page.waitForTimeout(2000);
    }}

    const html = await page.content();
    fs.writeFileSync('{html_file.replace('\\\\', '\\\\\\\\')}', html, 'utf-8');
    console.log('HTML saved: ' + html.length + ' bytes');

    await browser.close();
}})();
"""

# 先确认 playwright_chrome.exe 是否存在
chrome_path = os.path.join(work_dir, 'playwright_chrome.exe')
if not os.path.exists(chrome_path):
    # 使用系统路径
    chrome_path = r'C:\Users\Administrator\AppData\Local\ms-playwright\chromium-1228\chrome-win64\chrome.exe'

script = f"""
const fs = require('fs');
const {{ chromium }} = require('playwright');

(async () => {{
    const cookies = JSON.parse(fs.readFileSync(r'{work_dir}\\conny_cookies.json', 'utf8'));
    const browser = await chromium.launch({{
        headless: true,
        executablePath: r'{chrome_path}'
    }});
    const context = await browser.newContext({{
        userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
        cookies: cookies
    }});
    const page = await context.newPage();

    await page.goto('https://x.com/{username}', {{ waitUntil: 'domcontentloaded', timeout: 30000 }});
    await page.waitForTimeout(5000);

    const html = await page.content();
    fs.writeFileSync(r'{html_file}', html, 'utf-8');
    console.log('HTML saved: ' + html.length + ' bytes');

    await browser.close();
}})();
"""

script_file = os.path.join(work_dir, 'scrape_temp.js')
with open(script_file, 'w', encoding='utf-8') as f:
    f.write(script)

result = subprocess.run(
    ['node', script_file],
    cwd=work_dir,
    capture_output=True,
    text=True,
    timeout=60
)
print(result.stdout)
if result.stderr:
    print('STDERR:', result.stderr)

if not os.path.exists(html_file):
    print(f'HTML 文件未生成: {html_file}')
    sys.exit(1)

# Step 2: 从 HTML 提取推文
print('解析 HTML...')
html = open(html_file, encoding='utf-8').read()

# 提取所有 meta[content=... itemprop="articleBody"]
pattern = r'<meta content="([^"]+)"\s+itemprop="articleBody">'
tweets = []
seen = set()

for match in re.finditer(pattern, html, re.DOTALL):
    text = match.group(1).strip()
    # 清理
    text = re.sub(r'https?://\S+', '', text).strip()
    text = re.sub(r'\s+', ' ', text).strip()
    
    if len(text) < 10:
        continue
    if text in seen:
        continue
    seen.add(text)
    
    # 提取日期（向前搜索）
    before = html[max(0, match.start()-500):match.start()]
    date_match = re.search(r'itemprop="datePublished"\s+content="([^"]+)"', before)
    date = date_match.group(1) if date_match else ''
    
    # 提取图片
    after = html[match.end():match.end()+500]
    img_match = re.search(r'itemprop="image"\s+content="([^"]+)"', after)
    has_image = bool(img_match)
    
    tweets.append({
        'text': text,
        'date': date,
        'has_image': has_image
    })

print(f'提取到 {len(tweets)} 条推文')

# Step 3: 保存结果
output = {
    'username': username,
    'scraped_at': __import__('datetime').datetime.utcnow().isoformat() + 'Z',
    'tweet_count': len(tweets),
    'tweets': tweets
}

output_file = os.path.join(work_dir, 'data', f'{username}_tweets_new.json')
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f'结果已保存: {output_file}')
print(json.dumps(output, ensure_ascii=False, indent=2)[:2000])
