"""
抓取 @kkdtym 账号数据
"""
import json
import os
import re
import time
from datetime import datetime
from playwright.sync_api import sync_playwright

PROJECT_DIR = r'F:\Users\Administrator\Documents\WorkBuddy\2026-07-24-21-36-14'
DATA_DIR = os.path.join(PROJECT_DIR, 'data')
username = 'kkdtym'


def fetch_account(username):
    """使用 Playwright 抓取账号数据"""
    cookies_path = os.path.join(PROJECT_DIR, 'browser_profile', 'Network', 'Cookies')
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        
        context = browser.new_context()
        if os.path.exists(cookies_path):
            import sqlite3
            conn = sqlite3.connect(cookies_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name, value, domain, path FROM cookies WHERE domain LIKE '%x.com'")
            rows = cursor.fetchall()
            cookies = []
            for row in rows:
                cookies.append({
                    'name': row[0],
                    'value': row[1],
                    'domain': row[2],
                    'path': row[3]
                })
            context.add_cookies(cookies)
            conn.close()
        
        page = context.new_page()
        
        print(f'访问 @{username} 主页...')
        page.goto(f'https://x.com/{username}', wait_until='domcontentloaded', timeout=60000)
        time.sleep(5)
        
        # 尝试点击敏感内容警告
        try:
            page.click('text=是，查看个人资料', timeout=5000)
            time.sleep(3)
        except:
            pass
        
        # 滚动加载推文
        print('滚动加载推文...')
        for _ in range(10):
            page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            time.sleep(2)
        
        # 提取推文链接
        links = page.evaluate('''() => {
            const links = [];
            document.querySelectorAll('a[href*="/status/"]').forEach(a => {
                links.push(a.href);
            });
            return links;
        }''')
        
        print(f'找到 {len(links)} 条推文链接')
        
        # 提取推文文本
        tweets = []
        seen_texts = set()
        for link in links[:100]:  # 限制处理数量
            try:
                tweet_id = link.split('/')[-1]
                # 获取推文详情
                page.goto(link, wait_until='domcontentloaded', timeout=10000)
                time.sleep(2)
                
                # 提取文本
                text = page.evaluate('''() => {
                    const tweet = document.querySelector('article [data-testid="tweetText"]');
                    return tweet ? tweet.textContent : '';
                }''')
                
                if text and len(text) > 2:
                    key = text[:100].lower()
                    if key not in seen_texts:
                        seen_texts.add(key)
                        is_retweet = 'Reposted' in page.inner_text('article') or '已转帖' in page.inner_text('article')
                        
                        tweets.append({
                            'tweet_id': tweet_id,
                            'text': text[:500],
                            'is_retweet': is_retweet,
                            'url': link,
                            'scraped_at': datetime.now().isoformat()
                        })
            except Exception as e:
                print(f'  处理推文失败: {e}')
                continue
        
        print(f'成功抓取 {len(tweets)} 条推文')
        
        # 提取 profile 信息
        profile = {}
        try:
            name = page.locator('[data-testid="DgMainPageProfile_Name"]').inner_text()
            profile['name'] = name
        except:
            pass
        
        try:
            bio = page.locator('[data-testid="DgUserDescriptionBody"]').inner_text()
            profile['bio'] = bio
        except:
            pass
        
        browser.close()
        
        result = {
            'username': username,
            'scraped_at': datetime.now().isoformat(),
            'source': 'playwright_dom',
            'profile': profile,
            'tweets_sample': tweets[:50]
        }
        
        output_path = os.path.join(DATA_DIR, f'{username}_tweets.json')
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        print(f'数据已保存到 {output_path}')
        return result


if __name__ == '__main__':
    fetch_account(username)
