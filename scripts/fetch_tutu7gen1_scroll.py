"""
使用 Playwright 抓取 @tutu7gen1 的推文数据 - 滚动加载后提取
"""
import json
import os
import re
import time
from datetime import datetime

from playwright.sync_api import sync_playwright

PROJECT_DIR = r"F:\Users\Administrator\Documents\WorkBuddy\2026-07-24-21-36-14"
DATA_DIR = os.path.join(PROJECT_DIR, "data")
username = "tutu7gen1"


def parse_engagement(text):
    """从推文文本末尾解析互动数据"""
    parts = text.strip().split('\n')
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


def extract_tweets(page, user):
    """从页面提取推文信息"""
    tweet_info = page.evaluate(f"""() => {{
        const links = document.querySelectorAll('a[href^="/{user}/status/"]');
        const results = [];
        const seen = new Set();

        for (const a of links) {{
            const href = a.getAttribute('href');
            const match = href.match(/\\/{user}\\/status\\/(\\d+)/);
            if (!match) continue;

            const tweetId = match[1];
            if (seen.has(tweetId)) continue;
            seen.add(tweetId);

            const parent = a.closest('div') || a.parentElement;
            if (!parent) continue;

            const text = parent.innerText || '';
            const timeEl = parent.querySelector('time');
            const datetime = timeEl ? timeEl.getAttribute('datetime') : '';
            const displayDate = timeEl ? timeEl.textContent : '';

            const repostedText = parent.innerText || '';
            const isRetweet = /Reposted|已转帖/.test(repostedText);

            results.push({{
                tweetId: tweetId,
                text: text.substring(0, 2000),
                isRetweet: isRetweet,
                datetime: datetime,
                displayDate: displayDate,
            }});
        }}

        return results;
    }}""")

    return tweet_info


def main():
    cookies_path = os.path.join(PROJECT_DIR, "cookies.json")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
        )

        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            ),
        )

        if os.path.exists(cookies_path):
            with open(cookies_path, "r") as f:
                cookies = json.load(f)
                context.add_cookies(cookies)

        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => false });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
            Object.defineProperty(navigator, 'languages', { get: () => ['zh-CN', 'zh', 'en'] });
            window.chrome = { runtime: {} };
        """)

        page = context.new_page()

        print(f"访问 @{username} 主页...")
        page.goto(f"https://x.com/{username}", wait_until="domcontentloaded", timeout=60000)
        time.sleep(10)

        # 获取 profile
        profile = {}
        try:
            name = page.locator('[data-testid="DgMainPageProfile_Name"]').inner_text()
            profile["name"] = name
        except Exception:
            pass

        try:
            bio = page.locator('[data-testid="DgMainPageProfile_Bio"]').inner_text()
            profile["bio"] = bio
        except Exception:
            pass

        try:
            followers = page.locator('a[href*="/followers"]').first.inner_text()
            profile["followers"] = followers
        except Exception:
            pass

        try:
            following = page.locator('a[href*="/following"]').first.inner_text()
            profile["following"] = following
        except Exception:
            pass

        print(f"Profile: {profile}")

        # 滚动加载推文
        all_tweet_ids = set()
        all_tweets_raw = []

        print("开始滚动加载推文...")
        for scroll_num in range(30):
            # 先提取当前页面的推文
            current_tweets = extract_tweets(page, username)
            new_count = 0
            for t in current_tweets:
                if t['tweetId'] not in all_tweet_ids:
                    all_tweet_ids.add(t['tweetId'])
                    all_tweets_raw.append(t)
                    new_count += 1

            if new_count == 0:
                print(f"  滚动 {scroll_num + 1}: 无新推文，停止")
                break

            print(f"  滚动 {scroll_num + 1}: 新增 {new_count} 条推文，累计 {len(all_tweet_ids)} 条")

            if len(all_tweet_ids) >= 80:
                print("  已达到目标数量，停止滚动")
                break

            # 滚动到底部
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(5)

        print(f"\n共提取到 {len(all_tweets_raw)} 条推文")

        # 去重并按时间排序
        seen_ids = set()
        tweets = []
        for info in all_tweets_raw:
            if info['tweetId'] not in seen_ids:
                seen_ids.add(info['tweetId'])
                tweets.append({
                    'tweet_id': info['tweetId'],
                    'text': info['text'],
                    'is_retweet': info['isRetweet'],
                    'datetime': info['datetime'] or datetime.now().isoformat(),
                    'display_date': info.get('displayDate', ''),
                })

        retweet_count = sum(1 for t in tweets if t.get('is_retweet'))
        original_count = len(tweets) - retweet_count
        print(f"原创: {original_count}, 转贴: {retweet_count}")

        # 解析互动数据
        for i, t in enumerate(tweets):
            engagement = parse_engagement(t.get('text', ''))
            tweets[i]['likes'] = engagement['likes']
            tweets[i]['replies'] = engagement['replies']
            tweets[i]['views'] = engagement['views']

        result = {
            'username': username,
            'scraped_at': datetime.now().isoformat(),
            'source': 'playwright_scroll',
            'profile': profile,
            'recent_tweets': tweets[:80],
        }

        output_path = os.path.join(DATA_DIR, f'{username}_tweets_scrolled.json')
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        print(f'数据已保存到 {output_path}')

        # 保存截图
        page.screenshot(path=os.path.join(DATA_DIR, f'{username}_screenshot5.png'))

        browser.close()


if __name__ == '__main__':
    main()
