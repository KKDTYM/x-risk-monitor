"""
抓取 @muumuujiang 的推文数据，用于 v4 风险评估
使用 Playwright 从推文详情页解析互动数据和 raw DOM
"""
import json
import os
import re
import time
from playwright.sync_api import sync_playwright

PROJECT_DIR = r"F:\Users\Administrator\Documents\WorkBuddy\2026-07-24-21-36-14"
DATA_DIR = os.path.join(PROJECT_DIR, "data")
TARGET_USERNAME = "muumuujiang"

def parse_engagement_from_raw(raw_text):
    """从 raw DOM 文本末尾解析互动数据"""
    parts = raw_text.strip().split('\n')
    last_lines = [l.strip() for l in parts if l.strip()]
    
    likes = 0
    retweets = 0
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
    
    if len(patterns) >= 2:
        replies = patterns[-2] if len(patterns) >= 3 else 0
        likes = patterns[-1] if len(patterns) >= 2 else 0
        views = patterns[-3] if len(patterns) >= 3 else 0
    
    return {'likes': likes, 'retweets': retweets, 'replies': replies, 'views': views}


def scrape_tweet_page(page, tweet_id):
    """抓取单条推文详情页"""
    url = f"https://x.com/{TARGET_USERNAME}/status/{tweet_id}"
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        time.sleep(3)  # 等待页面加载
        
        # 获取渲染后的 DOM
        content = page.content()
        raw_text = page.evaluate("""
            () => {
                let text = '';
                const article = document.querySelector('article');
                if (article) {
                    // 获取推文完整文本
                    const tweetText = article.querySelector('[data-testid="tweetText"]');
                    if (tweetText) {
                        text += tweetText.innerText;
                    }
                    // 获取互动数据（点赞、转发、回复、浏览量）
                    const metrics = article.querySelectorAll('div[data-testid="tweet"] > div > div');
                    for (let el of metrics) {
                        text += '\\n' + el.innerText;
                    }
                    // 获取时间
                    const timeEl = article.querySelector('time');
                    if (timeEl) {
                        text += '\\n' + timeEl.getAttribute('datetime');
                    }
                }
                return text;
            }
        """)
        
        return {
            'raw': raw_text,
            'tweet_id': tweet_id
        }
    except Exception as e:
        print(f"  Error fetching tweet {tweet_id}: {e}")
        return None


def main():
    # 读取 syndication 数据获取推文 ID 列表
    syndication_path = os.path.join(DATA_DIR, f"{TARGET_USERNAME}_tweets_syndication.json")
    with open(syndication_path, 'r', encoding='utf-8') as f:
        syndication_data = json.load(f)
    
    tweets = syndication_data.get('recent_tweets', [])
    profile = syndication_data.get('profile', {})
    
    print(f"抓取 @{TARGET_USERNAME} 的 {len(tweets)} 条推文详情...")
    
    # 使用 Playwright 抓取每条推文的完整数据
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080}
        )
        page = context.new_page()
        
        enhanced_tweets = []
        for i, tweet in enumerate(tweets):
            tweet_id = tweet.get('tweet_id')
            if not tweet_id:
                continue
            
            print(f"  [{i+1}/{len(tweets)}] 抓取推文 {tweet_id[:12]}...")
            
            result = scrape_tweet_page(page, tweet_id)
            if result:
                # 解析互动数据
                engagement = parse_engagement_from_raw(result['raw'])
                
                # 合并数据
                enhanced_tweet = {
                    **tweet,
                    'raw': result['raw'],
                    'likes': engagement['likes'],
                    'retweets_eng': engagement['retweets'],
                    'replies': engagement['replies'],
                    'views': engagement['views'],
                }
                enhanced_tweets.append(enhanced_tweet)
            else:
                # 抓取失败，保留原始数据
                enhanced_tweets.append(tweet)
            
            # 避免请求过快被限流
            if i < len(tweets) - 1:
                time.sleep(2)
        
        browser.close()
    
    # 保存增强数据
    output_path = os.path.join(DATA_DIR, f"{TARGET_USERNAME}_tweets_enhanced.json")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(enhanced_tweets, f, ensure_ascii=False, indent=2)
    
    # 统计
    with_likes = sum(1 for t in enhanced_tweets if t.get('likes', 0) > 0)
    print(f"\n抓取完成！共 {len(enhanced_tweets)} 条")
    print(f"其中 {with_likes} 条有互动数据")
    print(f"数据已保存到: {output_path}")
    
    return enhanced_tweets


if __name__ == "__main__":
    main()
