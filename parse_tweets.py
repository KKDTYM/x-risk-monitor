#!/usr/bin/env python3
"""从 HTML 提取推文"""
import re
import json
import sys

username = sys.argv[1] if len(sys.argv) > 1 else 'sunny31059'
html_file = f'data/html_{username}.html'

print(f'解析 {html_file} ...')
html = open(html_file, encoding='utf-8').read()

# 提取所有 meta[content=... itemprop="articleBody"]
tweets = []
seen = set()

for match in re.finditer(r'<meta content="(.*?)"\s+itemprop="articleBody">\s*<meta content="(.*?)"\s+itemprop="text">', html, re.DOTALL):
    article_body = match.group(1).strip()
    text = match.group(2).strip()
    
    # 清理 URL
    text = re.sub(r'https?://\S+', '', text).strip()
    # 清理多余空白
    text = re.sub(r'\s+', ' ', text).strip()
    
    if len(text) < 10:
        continue
    if text in seen:
        continue
    seen.add(text)
    
    # 提取日期（向前搜索 300 chars）
    before = html[max(0, match.start()-300):match.start()]
    date_match = re.search(r'itemprop="datePublished"\s+content="([^"]+)"', before)
    date = date_match.group(1) if date_match else ''
    
    # 提取图片（向后搜索 300 chars）
    after = html[match.end():match.end()+300]
    img_match = re.search(r'itemprop="image"\s+content="([^"]+)"', after)
    has_image = bool(img_match)
    
    tweets.append({
        'text': text,
        'date': date,
        'has_image': has_image
    })

print(f'提取到 {len(tweets)} 条推文')

# 保存
output = {
    'username': username,
    'scraped_at': __import__('datetime').datetime.utcnow().isoformat() + 'Z',
    'tweet_count': len(tweets),
    'tweets': tweets
}

output_file = f'data/{username}_tweets_new.json'
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f'结果保存: {output_file}')
print('\n前 3 条推文示例:')
for i, t in enumerate(tweets[:3]):
    print(f'{i+1}. [{t["date"]}] {t["text"][:100]}...')
