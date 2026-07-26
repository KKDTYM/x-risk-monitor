"""
使用 Playwright 抓取 @tutu7gen1 的推文数据 - 使用更通用的选择器
"""
import json
import os
import time
from datetime import datetime

from playwright.sync_api import sync_playwright

PROJECT_DIR = r"F:\Users\Administrator\Documents\WorkBuddy\2026-07-24-21-36-14"
DATA_DIR = os.path.join(PROJECT_DIR, "data")
username = "tutu7gen1"


def extract_engagement_from_raw(text):
    """从推文 raw 文本末尾解析互动数据"""
    parts = text.strip().split('\n')
    last_lines = [l.strip() for l in parts if l.strip()]

    likes = 0
    retweets_eng = 0
    replies = 0
    views = 0

    patterns = []
    for line in last_lines[-5:]:
        import re
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
        try:
            page.goto(
                f"https://x.com/{username}",
                wait_until="domcontentloaded",
                timeout=60000,
            )
            time.sleep(10)
        except Exception as e:
            print(f"加载超时: {e}")
            time.sleep(5)

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

        # 滚动加载推文 - 使用 div[data-testid="tweet"] 选择器
        tweets = []
        seen_texts = set()
        last_height = page.evaluate("document.body.scrollHeight")

        print("开始滚动加载推文...")
        for scroll_num in range(20):
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(4)

            new_height = page.evaluate("document.body.scrollHeight")
            if new_height == last_height:
                print("  页面高度不再变化，停止滚动")
                break
            last_height = new_height

            # 尝试多种选择器
            tweet_selectors = [
                'div[data-testid="tweet"]',
                'div[data-testid="tweetCell"]',
                'article',
            ]

            found_any = False
            for selector in tweet_selectors:
                elements = page.query_selector_all(selector)
                if elements:
                    print(f"  滚动 {scroll_num + 1}: 使用 '{selector}' 找到 {len(elements)} 个元素")
                    found_any = True
                    break

            if not found_any:
                print(f"  滚动 {scroll_num + 1}: 未找到任何匹配元素")
                continue

            for elem in elements:
                try:
                    text = elem.inner_text().strip()
                    if text and len(text) > 3:
                        key = text[:100].lower()
                        if key not in seen_texts:
                            seen_texts.add(key)
                            is_retweet = "Reposted" in text or "已转帖" in text

                            tweet_data = {
                                "text": text[:2000],
                                "is_retweet": is_retweet,
                                "datetime": datetime.now().isoformat(),
                            }
                            tweets.append(tweet_data)
                except Exception:
                    pass

            if len(tweets) >= 40:
                print("  已收集足够推文，停止滚动")
                break

        print(f"共抓取 {len(tweets)} 条推文")

        retweet_count = sum(1 for t in tweets if t.get("is_retweet"))
        original_count = len(tweets) - retweet_count
        print(f"原创: {original_count}, 转贴: {retweet_count}")

        # 解析互动数据
        for i, t in enumerate(tweets):
            engagement = extract_engagement_from_raw(t.get("text", ""))
            tweets[i]["likes"] = engagement["likes"]
            tweets[i]["replies"] = engagement["replies"]
            tweets[i]["views"] = engagement["views"]

        result = {
            "username": username,
            "scraped_at": datetime.now().isoformat(),
            "source": "playwright_stealth_v2",
            "profile": profile,
            "recent_tweets": tweets[:50],
        }

        output_path = os.path.join(DATA_DIR, f"{username}_tweets_v2.json")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        print(f"数据已保存到 {output_path}")
        browser.close()


if __name__ == "__main__":
    main()
