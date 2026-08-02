"""
处理敏感内容警告的 @tutu7gen1 抓取脚本
"""
import json
import re
import time
from datetime import datetime
from playwright.sync_api import sync_playwright

PROJECT_DIR = r'F:\Users\Administrator\Documents\WorkBuddy\2026-07-24-21-36-14'
DATA_DIR = f'{PROJECT_DIR}/data'

COOKIES = [
    {"domain": ".x.com", "name": "auth_token", "value": "0555da63fcf228b97af5aec8c8ed4fd6d5841880", "path": "/"},
    {"domain": ".x.com", "name": "guest_id", "value": "v1%3A178505847748990053", "path": "/"},
    {"domain": ".x.com", "name": "twid", "value": "u%3D2081335439026421760", "path": "/"},
    {"domain": ".x.com", "name": "_twitter_sess", "value": "BAh7BiIKZmxhc2hJQzonQWN0aW9uQ29udHJvbGxlcjo6Rmxhc2g6OkZsYXNo%250ASGFzaHsABjoKQHVzZWR7AA%253D%253D--1164b91ac812d853b877e93ddb612b7471bebc74", "path": "/"},
    {"domain": ".x.com", "name": "auth_multi", "value": "\"497862683:443bd09a5c16b0d8e346459f52686dc7be306564|1919756553915428864:a40bfcf10aa9fda18b4e1768fc6d63e567a9e5fc|1969781334114455552:3fe146efd1cc10b8179ef91e36f583d60a5c6e5b\"", "path": "/"},
    {"domain": ".x.com", "name": "__cf_bm", "value": "gC8t1L9RsF3ndSQTlNW44GTP2fH6WB_86U2pvCjlV0U-1785063263.959605-1.0.1.1-D4toXEYknP5RJOyGlG4sM_HGw_2jhgUL6VTmOmum3utpnst26y3miE8TIaLHHRcRuu3qv8JqEVPNwzCXxdysjZc5qHIsdtkUpC0.rWlSzPWSCfviWn93gZVSUwcOiu3D", "path": "/"},
    {"domain": ".x.com", "name": "ct0", "value": "bb33543802aefbd7f6b2496ef8ec78ec578d22decbc0b5a0fa2ff1d66846a7a57deff1cc2b0fbc16f7e3edb3b2bcb9b0758b128c9af16bf0133c44980671ba5f329812ffb971fdd03443edf83423e4ee", "path": "/"},
    {"domain": ".x.com", "name": "kdt", "value": "I26qcLfGtmQPKocgpIA1CmOPLRiS2kYQu8CY2vdA", "path": "/"},
    {"domain": ".x.com", "name": "personalization_id", "value": "\"v1_VF7XpjNa6DEkBMUivBb/xQ==\"", "path": "/"},
]

username = 'tutu7gen1'


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080}
        )
        
        for c in COOKIES:
            context.add_cookies([c])
        
        page = context.new_page()
        
        print(f'访问 @{username} 主页...')
        page.goto(f'https://x.com/{username}', wait_until='domcontentloaded', timeout=30000)
        time.sleep(5)
        
        # 检查是否有敏感内容警告
        try:
            sensitive_btn = page.locator('button:has-text("是，查看个人资料")').first
            if sensitive_btn.count() > 0:
                print('发现敏感内容警告，点击"是，查看个人资料"...')
                sensitive_btn.click()
                time.sleep(5)
        except Exception as e:
            print(f'未找到敏感内容警告按钮: {e}')
        
        # 截图确认
        page.screenshot(path=f'{DATA_DIR}/{username}_after_sensitive.png')
        
        print(f'Page title: {page.title()}')
        
        # 多次滚动加载推文
        print('开始滚动加载...')
        last_height = 0
        all_tweet_texts = []
        seen_texts = set()
        
        for scroll_num in range(50):
            page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            time.sleep(2)
            
            current_height = page.evaluate('document.body.scrollHeight')
            
            if current_height == last_height:
                print(f'  滚动 {scroll_num+1}: 高度未变化 ({current_height})，停止')
                break
            
            last_height = current_height
            
            # 提取推文文本（article 标签）
            articles = page.evaluate('''() => {
                const articles = Array.from(document.querySelectorAll('article'));
                return articles.slice(0, 100).map(a => a.innerText.trim());
            }''')
            
            new_tweets = []
            for text in articles:
                if text and len(text) > 10:
                    key = text[:50].lower()
                    if key not in seen_texts:
                        seen_texts.add(key)
                        new_tweets.append(text)
            
            if new_tweets:
                print(f'  滚动 {scroll_num+1}: 新增 {len(new_tweets)} 条推文，累计 {len(seen_texts)} 条')
                all_tweet_texts.extend(new_tweets)
        
        print(f'\n共抓取 {len(all_tweet_texts)} 条推文')
        
        # 统计原创/转贴
        retweet_count = sum(1 for t in all_tweet_texts if 'Reposted' in t or '已转帖' in t)
        original_count = len(all_tweet_texts) - retweet_count
        
        print(f'原创: {original_count}, 转贴: {retweet_count}')
        
        # 输出结果
        output = {
            'username': username,
            'scraped_at': datetime.now().isoformat(),
            'source': 'playwright_with_sensitive_handler',
            'profile': {
                'followers': '84.9K',
                'following': '243',
                'posts': '372',
            },
            'tweets_sample': all_tweet_texts[:30],  # 前 30 条
            'total_tweets_found': len(all_tweet_texts),
        }
        
        output_path = f'{DATA_DIR}/{username}_tweets_sensitive.json'
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        
        print(f'\n数据已保存到 {output_path}')
        
        browser.close()


if __name__ == '__main__':
    main()
