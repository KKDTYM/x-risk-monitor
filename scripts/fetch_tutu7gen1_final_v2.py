"""
最终方案：使用 Playwright + 延长等待 + 多次滚动获取 @tutu7gen1 推文
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
        time.sleep(10)
        
        # 截图确认
        page.screenshot(path=f'{DATA_DIR}/{username}_final_check.png')
        
        # 获取页面标题确认登录状态
        print(f'Page title: {page.title()}')
        
        # 多次滚动，每次间隔更长
        print('开始滚动加载...')
        last_height = 0
        all_tweet_links = set()
        
        for scroll_num in range(30):
            # 滚动到底部
            page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            time.sleep(3)
            
            # 提取所有推文链接
            links = page.evaluate('''() => {
                const links = Array.from(document.querySelectorAll('a'));
                const tweetLinks = links
                    .filter(l => {
                        const href = l.getAttribute('href') || '';
                        return href.includes('/status/') && href.includes('/tutu7gen1/');
                    })
                    .map(l => l.getAttribute('href'));
                return [...new Set(tweetLinks)];
            }''')
            
            current_height = page.evaluate('document.body.scrollHeight')
            
            if len(links) > len(all_tweet_links):
                print(f'  滚动 {scroll_num+1}: 新增 {len(links) - len(all_tweet_links)} 条，累计 {len(links)} 条')
                all_tweet_links.update(links)
            elif current_height == last_height:
                print(f'  滚动 {scroll_num+1}: 高度未变化 ({current_height})，停止')
                break
            
            last_height = current_height
        
        print(f'\n共找到 {len(all_tweet_links)} 条推文链接')
        
        # 提取推文详细信息
        tweets = []
        seen_ids = set()
        
        for link in list(all_tweet_links)[:100]:  # 限制处理数量
            match = re.search(r'/status/(\d+)', link)
            if match:
                tweet_id = match.group(1)
                if tweet_id not in seen_ids:
                    seen_ids.add(tweet_id)
                    
                    # 点击推文获取详情
                    try:
                        page.goto(f'https://x.com/tutu7gen1/status/{tweet_id}', wait_until='domcontentloaded', timeout=15000)
                        time.sleep(2)
                        
                        # 获取推文文本
                        text = ''
                        try:
                            tweet_card = page.locator('[data-testid="tweetCard"]').first
                            if tweet_card.count() > 0:
                                text = tweet_card.inner_text()
                        except:
                            pass
                        
                        # 获取发布时间
                        datetime_str = ''
                        try:
                            time_elem = page.locator('time').first
                            if time_elem.count() > 0:
                                datetime_str = time_elem.get_attribute('datetime', timeout=1000) or ''
                        except:
                            pass
                        
                        tweet_data = {
                            'tweet_id': tweet_id,
                            'text': text[:2000].strip(),
                            'created_at': datetime_str,
                            'is_retweet': False,  # 需要进一步判断
                            'url': link,
                        }
                        tweets.append(tweet_data)
                    except Exception as e:
                        print(f'  获取推文 {tweet_id} 失败: {e}')
                        continue
        
        browser.close()
        
        # 输出结果
        output = {
            'username': username,
            'scraped_at': datetime.now().isoformat(),
            'source': 'playwright_enhanced',
            'total_links_found': len(all_tweet_links),
            'tweets_detail': tweets[:20],  # 只保留前 20 条详情
        }
        
        output_path = f'{DATA_DIR}/{username}_tweets_final_v2.json'
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        
        print(f'\n数据已保存到 {output_path}')
        print(f'共获取 {len(tweets)} 条推文详情')


if __name__ == '__main__':
    main()
