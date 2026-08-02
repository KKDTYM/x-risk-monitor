"""
检查 @tutu7gen1 页面的 DOM 结构
"""
import json
import os
import time

from playwright.sync_api import sync_playwright

PROJECT_DIR = r"F:\Users\Administrator\Documents\WorkBuddy\2026-07-24-21-36-14"
DATA_DIR = os.path.join(PROJECT_DIR, "data")
username = "tutu7gen1"


def main():
    cookies_path = os.path.join(PROJECT_DIR, "cookies.json")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

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

        # 截图
        page.screenshot(path=os.path.join(DATA_DIR, f"{username}_screenshot3.png"))

        # 获取所有带有 data-testid 的元素类型
        test_ids = page.evaluate("""() => {
            const elements = document.querySelectorAll('[data-testid]');
            const ids = new Set();
            elements.forEach(el => {
                ids.add(el.getAttribute('data-testid'));
            });
            return Array.from(ids).sort();
        }""")

        print(f"\n页面中所有 data-testid 值 ({len(test_ids)} 个唯一值):")
        for tid in test_ids:
            print(f"  - {tid}")

        # 统计不同选择器的元素数量
        selectors_to_check = [
            'div[data-testid]',
            'article',
            'section',
            'a[href^="/tutu7gen1/status/"]',
        ]

        print("\n--- 元素计数 ---")
        for sel in selectors_to_check:
            count = page.evaluate(f'document.querySelectorAll(`{sel}`).length')
            print(f"  {sel}: {count}")

        # 尝试获取推文链接
        tweet_links = page.evaluate("""() => {
            const links = document.querySelectorAll('a[href^="/tutu7gen1/status/"]');
            return Array.from(links).map(a => a.getAttribute('href')).slice(0, 10);
        }""")

        print(f"\n推文链接 ({len(tweet_links)} 个):")
        for link in tweet_links:
            print(f"  {link}")

        # 尝试获取所有推文时间戳
        timestamps = page.evaluate("""() => {
            const timeEls = document.querySelectorAll('a[href*="/status/"] time');
            return Array.from(timeEls).map(el => el.getAttribute('datetime')).slice(0, 10);
        }""")

        print(f"\n时间戳 ({len(timestamps)} 个):")
        for ts in timestamps:
            print(f"  {ts}")

        browser.close()


if __name__ == "__main__":
    main()
