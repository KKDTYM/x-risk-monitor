"""
使用 Playwright 抓取 @muumuujiang 的推文数据
需要用户已登录的 Chrome cookies
"""
import json
import os
import re
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from playwright.sync_api import sync_playwright

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_DIR, 'data')

def parse_engagement_from_raw(raw_text):
    """从 raw 文本末尾解析互动数据（点赞/转发/回复/浏览量）"""
    parts = raw_text.strip().split('\n')
    last_lines = [l.strip() for l in parts if l.strip()]
    
    likes = 0
    retweets_eng = 0
    replies = 0
    views = 0
    
    patterns = []
    for line in last_lines[-5:]:
        num = re.search(r'([\d,]+)', line)
        if num:
            patterns.append(int(num.group(1).replace(',', '')))
        else:
            cn = re.search(r'(\d+)万', line)
            if cn:
                patterns.append(int(cn.group(1)) * 10000)
    
    if len(patterns) >= 3:
        replies = patterns[-3]
        likes = patterns[-2]
        views = patterns[-1] if patterns[-1] > 100 else 0
    
    return {'likes': likes, 'retweets': retweets_eng, 'replies': replies, 'views': views}

def fetch_with_playwright(username):
    """使用 Playwright 抓取推文"""
    cookies_path = os.path.join(PROJECT_DIR, 'cookies.json')
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        
        # 尝试加载 cookies
        context = browser.new_context()
        if os.path.exists(cookies_path):
            with open(cookies_path, 'r') as f:
                cookies = json.load(f)
                context.add_cookies(cookies)
        
        page = context.new_page()
        
        print(f'访问 @{username} 主页...')
        page.goto(f'https://x.com/{username}', wait_until='domcontentloaded', timeout=60000)
        time.sleep(5)
        
        # 获取 profile 信息
        profile = {}
        try:
            name = page.locator('[data-testid="DgMainPageProfile_Name"]').inner_text()
            profile['name'] = name
        except:
            pass
        
        try:
            followers = page.locator('a[href*="/followers"]').first.inner_text()
            profile['followers'] = followers
        except:
            pass
        
        try:
            following = page.locator('a[href*="/following"]').first.inner_text()
            profile['following'] = following
        except:
            pass
        
        print(f'Profile: {profile}')
        
        # 滚动页面加载推文
        tweets = []
        last_height = page.evaluate('document.body.scrollHeight')
        
        print('开始滚动加载推文...')
        for scroll_num in range(10):  # 最多滚动 10 次
            page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            time.sleep(2)
            
            new_height = page.evaluate('document.body.scrollHeight')
            if new_height == last_height:
                break
            last_height = new_height
            
            # 提取推文
            tweet_elements = page.query_selector_all('article[data-testid="tweet"]')
            print(f'  滚动 {scroll_num+1}: 找到 {len(tweet_elements)} 条推文')
            
            for elem in tweet_elements:
                try:
                    tweet_data = {
                        'text': elem.inner_text()[:500],
                        'raw': elem.inner_text(),
                        'is_retweet': 'Reposted' in elem.inner_text() or '已转帖' in elem.inner_text(),
                        'datetime': datetime.now().isoformat(),
                    }
                    tweets.append(tweet_data)
                except:
                    pass
        
        # 去重
        seen = set()
        unique_tweets = []
        for t in tweets:
            key = t['text'][:100]
            if key not in seen:
                seen.add(key)
                unique_tweets.append(t)
        
        print(f'共抓取 {len(unique_tweets)} 条唯一推文')
        
        # 解析互动数据
        for i, t in enumerate(unique_tweets):
            engagement = parse_engagement_from_raw(t.get('raw', ''))
            unique_tweets[i]['likes'] = engagement['likes']
            unique_tweets[i]['replies'] = engagement['replies']
            unique_tweets[i]['views'] = engagement['views']
        
        browser.close()
        
        return {
            'profile': profile,
            'recent_tweets': unique_tweets,
            'scraped_at': datetime.now().isoformat(),
            'source': 'playwright_dom',
        }

if __name__ == '__main__':
    username = 'muumuujiang'
    result = fetch_with_playwright(username)
    
    output_path = os.path.join(DATA_DIR, f'{username}_tweets_playwright.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f'\n保存到: {output_path}')
    print(f'推文数: {len(result["recent_tweets"])}')
    
    # 统计转贴
    retweet_count = sum(1 for t in result['recent_tweets'] if t.get('is_retweet'))
    original_count = len(result['recent_tweets']) - retweet_count
    print(f'原创: {original_count}, 转贴: {retweet_count}')
