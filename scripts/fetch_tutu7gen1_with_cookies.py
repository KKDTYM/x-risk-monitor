"""
使用用户 cookies 抓取 @tutu7gen1 推文
尝试 syndication API + GraphQL + Playwright DOM 解析
"""
import json
import os
import re
import time
from datetime import datetime
from playwright.sync_api import sync_playwright

PROJECT_DIR = r'F:\Users\Administrator\Documents\WorkBuddy\2026-07-24-21-36-14'
DATA_DIR = os.path.join(PROJECT_DIR, 'data')

# 用户提供的 cookies
COOKIES = [
    {"domain": ".x.com", "expirationDate": 1816600103.098764, "hostOnly": False, "httpOnly": True, "name": "auth_token", "path": "/", "sameSite": "no_restriction", "secure": True, "session": False, "storeId": None, "value": "0555da63fcf228b97af5aec8c8ed4fd6d5841880"},
    {"domain": ".x.com", "expirationDate": 1819618477.028269, "hostOnly": False, "httpOnly": False, "name": "guest_id", "path": "/", "sameSite": "no_restriction", "secure": True, "session": False, "storeId": None, "value": "v1%3A178505847748990053"},
    {"domain": ".x.com", "expirationDate": 1819618476.635722, "hostOnly": False, "httpOnly": False, "name": "ads_prefs", "path": "/", "sameSite": "no_restriction", "secure": True, "session": False, "storeId": None, "value": "\"HBIRAAA=\""},
    {"domain": ".x.com", "expirationDate": 1816600258.465055, "hostOnly": False, "httpOnly": False, "name": "twid", "path": "/", "sameSite": "no_restriction", "secure": True, "session": False, "storeId": None, "value": "u%3D2081335439026421760"},
    {"domain": ".x.com", "hostOnly": False, "httpOnly": True, "name": "_twitter_sess", "path": "/", "sameSite": None, "secure": True, "session": True, "storeId": None, "value": "BAh7BiIKZmxhc2hJQzonQWN0aW9uQ29udHJvbGxlcjo6Rmxhc2g6OkZsYXNo%250ASGFzaHsABjoKQHVzZWR7AA%253D%253D--1164b91ac812d853b877e93ddb612b7471bebc74"},
    {"domain": ".x.com", "expirationDate": 1819624250.480158, "hostOnly": False, "httpOnly": True, "name": "auth_multi", "path": "/", "sameSite": "lax", "secure": True, "session": False, "storeId": None, "value": "\"497862683:443bd09a5c16b0d8e346459f52686dc7be306564|1919756553915428864:a40bfcf10aa9fda18b4e1768fc6d63e567a9e5fc|1969781334114455552:3fe146efd1cc10b8179ef91e36f583d60a5c6e5b\""},
    {"domain": ".x.com", "expirationDate": 1785065063.405039, "hostOnly": False, "httpOnly": True, "name": "__cf_bm", "path": "/", "sameSite": "no_restriction", "secure": True, "session": False, "storeId": None, "value": "gC8t1L9RsF3ndSQTlNW44GTP2fH6WB_86U2pvCjlV0U-1785063263.959605-1.0.1.1-D4toXEYknP5RJOyGlG4sM_HGw_2jhgUL6VTmOmum3utpnst26y3miE8TIaLHHRcRuu3qv8JqEVPNwzCXxdysjZc5qHIsdtkUpC0.rWlSzPWSCfviWn93gZVSUwcOiu3D"},
    {"domain": ".x.com", "expirationDate": 1819624103.742303, "hostOnly": False, "httpOnly": False, "name": "ct0", "path": "/", "sameSite": "lax", "secure": True, "session": False, "storeId": None, "value": "bb33543802aefbd7f6b2496ef8ec78ec578d22decbc0b5a0fa2ff1d66846a7a57deff1cc2b0fbc16f7e3edb3b2bcb9b0758b128c9af16bf0133c44980671ba5f329812ffb971fdd03443edf83423e4ee"},
    {"domain": ".x.com", "expirationDate": 1819624249.835153, "hostOnly": False, "httpOnly": False, "name": "guest_id_ads", "path": "/", "sameSite": "no_restriction", "secure": True, "session": False, "storeId": None, "value": "v1%3A178505847748990053"},
    {"domain": ".x.com", "expirationDate": 1819624249.835252, "hostOnly": False, "httpOnly": False, "name": "guest_id_marketing", "path": "/", "sameSite": "no_restriction", "secure": True, "session": False, "storeId": None, "value": "v1%3A178505847748990053"},
    {"domain": ".x.com", "expirationDate": 1819624103.098585, "hostOnly": False, "httpOnly": True, "name": "kdt", "path": "/", "sameSite": None, "secure": True, "session": False, "storeId": None, "value": "I26qcLfGtmQPKocgpIA1CmOPLRiS2kYQu8CY2vdA"},
    {"domain": ".x.com", "expirationDate": 1819609695.890338, "hostOnly": False, "httpOnly": False, "name": "personalization_id", "path": "/", "sameSite": "no_restriction", "secure": True, "session": False, "storeId": None, "value": "\"v1_VF7XpjNa6DEkBMUivBb/xQ==\""},
]

username = 'tutu7gen1'


def fetch_with_syndication():
    """尝试 syndication API"""
    print("\n=== 方法 1: Syndication API ===")
    import requests
    
    api_url = f'https://syndication.twitter.com/srv/accountProfileList/user/{username}/0'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Authorization': 'Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGGrjMc',
        'Cookie': '; '.join([f"{c['name']}={c['value']}" for c in COOKIES])
    }
    
    try:
        resp = requests.get(api_url, headers=headers, timeout=15)
        print(f'Status: {resp.status_code}')
        if resp.status_code == 200:
            data = resp.json()
            tweets = data.get('tweets', [])
            print(f'Tweets count: {len(tweets)}')
            if tweets:
                return {'source': 'syndication', 'tweets': tweets[:50]}
        else:
            print(f'Error: {resp.text[:200]}')
    except Exception as e:
        print(f'Exception: {e}')
    
    return None


def fetch_with_playwright():
    """使用 Playwright + cookies 抓取"""
    print("\n=== 方法 2: Playwright DOM 解析 ===")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        
        # 创建 context 并添加 cookies
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080}
        )
        
        # 添加 cookies
        for c in COOKIES:
            cookie = {
                'name': c['name'],
                'value': c['value'],
                'domain': c['domain'],
                'path': c.get('path', '/'),
            }
            if c.get('expirationDate'):
                cookie['expires'] = int(c['expirationDate'])
            if c.get('httpOnly'):
                cookie['httpOnly'] = c['httpOnly']
            if c.get('secure'):
                cookie['secure'] = c['secure']
            context.add_cookies([cookie])
        
        page = context.new_page()
        
        # 访问主页
        print(f'访问 @{username} 主页...')
        try:
            page.goto(f'https://x.com/{username}', wait_until='domcontentloaded', timeout=30000)
            time.sleep(5)
        except Exception as e:
            print(f'加载超时: {e}')
        
        # 获取 profile 信息
        profile = {}
        try:
            # 尝试获取昵称
            name_elem = page.locator('[data-testid="DgMainPageProfile_Name"]').first
            if name_elem.count() > 0:
                profile['name'] = name_elem.inner_text()
        except:
            pass
        
        try:
            # 获取粉丝数
            followers_elem = page.locator('a[href$="/followers"]').first
            if followers_elem.count() > 0:
                profile['followers'] = followers_elem.inner_text()
        except:
            pass
        
        try:
            # 获取关注数
            following_elem = page.locator('a[href$="/following"]').first
            if following_elem.count() > 0:
                profile['following'] = following_elem.inner_text()
        except:
            pass
        
        print(f'Profile: {profile}')
        
        # 提取推文（基于链接模式）
        print('开始提取推文...')
        tweets = []
        seen_ids = set()
        
        # 先提取当前可见的推文
        tweet_links = page.locator('a[href*="/status/"]').all()
        print(f'找到 {len(tweet_links)} 条推文链接')
        
        for link in tweet_links[:100]:  # 限制提取数量
            try:
                href = link.get_attribute('href')
                if href:
                    # 提取 tweet_id
                    match = re.search(r'/status/(\d+)', href)
                    if match:
                        tweet_id = match.group(1)
                        if tweet_id not in seen_ids:
                            seen_ids.add(tweet_id)
                            
                            # 获取推文文本
                            parent = link.evaluate_handle('el => el.closest("article")')
                            if parent:
                                text = parent.inner_text()
                                if text and len(text.strip()) > 0:
                                    is_retweet = 'Reposted' in text or '已转帖' in text
                                    
                                    tweet_data = {
                                        'tweet_id': tweet_id,
                                        'text': text[:2000].strip(),
                                        'is_retweet': is_retweet,
                                        'url': href,
                                        'datetime': datetime.now().isoformat(),
                                    }
                                    tweets.append(tweet_data)
            except:
                pass
        
        print(f'提取到 {len(tweets)} 条推文')
        
        # 尝试滚动加载更多
        if len(tweets) < 20:
            print('推文数量不足，尝试滚动加载更多...')
            last_count = len(tweets)
            for scroll_num in range(20):
                page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                time.sleep(2)
                
                new_links = page.locator('a[href*="/status/"]').all()
                if len(new_links) <= last_count:
                    break
                last_count = len(new_links)
                
                for link in new_links[last_count:last_count+50]:
                    try:
                        href = link.get_attribute('href')
                        if href:
                            match = re.search(r'/status/(\d+)', href)
                            if match:
                                tweet_id = match.group(1)
                                if tweet_id not in seen_ids:
                                    seen_ids.add(tweet_id)
                                    
                                    parent = link.evaluate_handle('el => el.closest("article")')
                                    if parent:
                                        text = parent.inner_text()
                                        if text and len(text.strip()) > 0:
                                            is_retweet = 'Reposted' in text or '已转帖' in text
                                            
                                            tweet_data = {
                                                'tweet_id': tweet_id,
                                                'text': text[:2000].strip(),
                                                'is_retweet': is_retweet,
                                                'url': href,
                                                'datetime': datetime.now().isoformat(),
                                            }
                                            tweets.append(tweet_data)
                    except:
                        pass
                
                print(f'  滚动 {scroll_num+1}: 累计 {len(tweets)} 条')
        
        browser.close()
        
        return {'source': 'playwright_dom', 'profile': profile, 'tweets': tweets}


def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    
    # 方法 1: Syndication API
    result = fetch_with_syndication()
    
    # 方法 2: Playwright
    pw_result = fetch_with_playwright()
    
    # 合并结果
    output = {
        'username': username,
        'scraped_at': datetime.now().isoformat(),
        'profile': pw_result.get('profile', {}),
        'tweets': pw_result.get('tweets', []),
    }
    
    # 保存
    output_path = os.path.join(DATA_DIR, f'{username}_tweets_enhanced.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f'\n数据已保存到 {output_path}')
    print(f'共抓取 {len(output["tweets"])} 条推文')
    
    # 统计原创/转贴
    retweet_count = sum(1 for t in output['tweets'] if t.get('is_retweet'))
    original_count = len(output['tweets']) - retweet_count
    print(f'原创: {original_count}, 转贴: {retweet_count}')


if __name__ == '__main__':
    main()
