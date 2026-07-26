"""
使用 Playwright 抓取 @tutu7gen1 的推文数据
"""
import json
import os
import time
from datetime import datetime

from playwright.sync_api import sync_playwright

PROJECT_DIR = r"F:\Users\Administrator\Documents\WorkBuddy\2026-07-24-21-36-14"
DATA_DIR = os.path.join(PROJECT_DIR, "data")
username = "tutu7gen1"


def main():
    cookies_path = os.path.join(PROJECT_DIR, "cookies.json")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        context = browser.new_context()
        if os.path.exists(cookies_path):
            with open(cookies_path, "r") as f:
                cookies = json.load(f)
                context.add_cookies(cookies)

        page = context.new_page()

        print(f"访问 @{username} 主页...")
        try:
            page.goto(
                f"https://x.com/{username}",
                wait_until="domcontentloaded",
                timeout=60000,
            )
            time.sleep(8)
        except Exception as e:
            print(f"加载超时: {e}")

        # 获取 profile 信息
        profile = {}
        try:
            name = page.locator('[data-testid="DgMainPageProfile_Name"]').inner_text()
            profile["name"] = name
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

        # 滚动页面加载推文
        tweets = []
        seen_texts = set()
        last_height = page.evaluate("document.body.scrollHeight")

        print("开始滚动加载推文...")
        for scroll_num in range(15):
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(3)

            new_height = page.evaluate("document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

            tweet_elements = page.query_selector_all('article[data-testid="tweet"]')
            print(f"  滚动 {scroll_num + 1}: 找到 {len(tweet_elements)} 条推文")

            for elem in tweet_elements:
                try:
                    text = elem.inner_text().strip()
                    if text and len(text) > 2:
                        key = text[:100].lower()
                        if key not in seen_texts:
                            seen_texts.add(key)
                            is_retweet = "Reposted" in text or "已转帖" in text

                            tweet_data = {
                                "text": text[:1000],
                                "is_retweet": is_retweet,
                                "datetime": datetime.now().isoformat(),
                            }
                            tweets.append(tweet_data)
                except Exception:
                    pass

        print(f"共抓取 {len(tweets)} 条唯一推文")

        retweet_count = sum(1 for t in tweets if t.get("is_retweet"))
        original_count = len(tweets) - retweet_count
        print(f"原创: {original_count}, 转贴: {retweet_count}")

        result = {
            "username": username,
            "scraped_at": datetime.now().isoformat(),
            "source": "playwright_dom",
            "profile": profile,
            "recent_tweets": tweets[:50],
        }

        output_path = os.path.join(DATA_DIR, f"{username}_tweets_playwright.json")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        print(f"数据已保存到 {output_path}")
        browser.close()


if __name__ == "__main__":
    main()
