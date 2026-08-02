#!/usr/bin/env python3
"""用 Fxtwitter API 抓取推文"""
import requests
import json
import sys
import os

username = sys.argv[1] if len(sys.argv) > 1 else 'sunny31059'
username = username.replace('@', '')

# Fxtwitter API
url = f'https://fxtwitter.com/{username}/status'
# 或者用 API 端点
api_url = f'https://api.fxtwitter.com/{username}'

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
    'Accept': 'application/json',
}

print(f'访问 {username} ...')
print(f'API URL: {api_url}')

try:
    resp = requests.get(api_url, headers=headers, timeout=30)
    print(f'状态码: {resp.status_code}')

    if resp.status_code == 200:
        data = resp.json()
        print(json.dumps(data, ensure_ascii=False, indent=2)[:2000])
    else:
        print(f'错误: {resp.text[:500]}')

except Exception as e:
    print(f'异常: {e}')
