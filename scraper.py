#!/usr/bin/env python3
"""
数据采集层：使用 Playwright headless 模式采集 X 账号数据
"""
import asyncio
import json
import random
import time
from playwright.async_api import async_playwright


class XScraper:
    """X 账号数据采集器"""

    def __init__(self, config):
        self.config = config
        self.tweets_count = config.get("scraper", {}).get("tweets_count", 15)
        self.timeout_ms = config.get("scraper", {}).get("timeout_ms", 30000)
        self.retry_count = config.get("scraper", {}).get("retry_count", 1)
        self.playwright = None
        self.browser = None

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop()

    async def start(self):
        """启动浏览器"""
        self.playwright = await async_playwright().start()
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        ]
        self.browser = await self.playwright.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
            ]
        )
        self.current_ua = random.choice(user_agents)
        return self

    async def stop(self):
        """关闭浏览器"""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    async def scrape_account(self, username):
        """采集单个账号的完整数据"""
        result = {
            "username": username,
            "scraped_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "error": None
        }

        for attempt in range(self.retry_count + 1):
            try:
                page = await self.browser.new_page(user_agent=self.current_ua)
                url = f"https://x.com/{username}"

                # 导航到页面
                response = await page.goto(url, timeout=self.timeout_ms, wait_until="domcontentloaded")

                # 等待内容加载
                try:
                    await page.wait_for_load_state("networkidle", timeout=10000)
                except:
                    pass  # 超时不影响，已有基础数据

                # 随机延迟模拟人类行为
                await asyncio.sleep(random.uniform(1, 2))

                # 提取账号基本信息
                profile_data = await self._extract_profile(page)
                result.update(profile_data)

                # 提取最近推文
                tweets_data = await self._extract_recent_tweets(page)
                result["recent_tweets"] = tweets_data

                # 提取账号状态
                status_data = await self._check_account_status(page)
                result.update(status_data)

                await page.close()
                return result

            except Exception as e:
                result["error"] = str(e)
                if attempt < self.retry_count:
                    await asyncio.sleep(random.uniform(2, 4))
                else:
                    return result

    async def _extract_profile(self, page):
        """提取账号基本信息"""
        data = {
            "followers": None,
            "following": None,
            "tweet_count": None,
            "bio": "",
            "registered_date": "",
            "is_sensitive": False
        }

        try:
            # 使用 JavaScript 提取数据
            profile_data = await page.evaluate("""() => {
                const result = {};

                // 提取粉丝数
                const followersEl = document.querySelector('[data-testid="followersCount"]');
                if (followersEl) {
                    result.followers = followersEl.textContent.trim();
                }

                // 提取关注数
                const followingEl = document.querySelector('[data-testid="followingCount"]');
                if (followingEl) {
                    result.following = followingEl.textContent.trim();
                }

                // 提取推文数
                const tweetCountEl = document.querySelector('[data-testid="tweetCount"]');
                if (tweetCountEl) {
                    result.tweet_count = tweetCountEl.textContent.trim();
                }

                // 提取 bio
                const bioEl = document.querySelector('[data-testid="UserDescription"]');
                if (bioEl) {
                    result.bio = bioEl.textContent.trim();
                }

                // 提取敏感标记
                const sensitiveEl = document.querySelector('[data-testid="AppTab_Sensitive"]');
                result.is_sensitive = sensitiveEl !== null;

                return result;
            }""")

            # 解析粉丝数（去除 K/M 等单位）
            followers_str = profile_data.get("followers", "")
            if followers_str:
                data["followers"] = self._parse_number(followers_str)

            following_str = profile_data.get("following", "")
            if following_str:
                data["following"] = self._parse_number(following_str)

            tweet_count_str = profile_data.get("tweet_count", "")
            if tweet_count_str:
                data["tweet_count"] = self._parse_number(tweet_count_str)

            data["bio"] = profile_data.get("bio", "")
            data["is_sensitive"] = profile_data.get("is_sensitive", False)

        except Exception as e:
            pass  # 返回默认值

        return data

    async def _extract_recent_tweets(self, page, count=15):
        """提取最近推文"""
        tweets = []

        try:
            # 滚动加载推文
            for i in range(3):
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(0.5)

            # 提取推文数据
            tweets_data = await page.evaluate(f"""() => {{
                const tweetElements = document.querySelectorAll('[data-testid="tweet"]');
                const tweets = [];
                const limit = Math.min({count}, tweetElements.length);

                for (let i = 0; i < limit; i++) {{
                    const el = tweetElements[i];
                    const tweet = {{}};

                    // 推文文本
                    const textEl = el.querySelector('[data-testid="tweetText"]');
                    tweet.text = textEl ? textEl.textContent.trim() : '';

                    // 发布时间
                    const timeEl = el.querySelector('time');
                    tweet.date = timeEl ? timeEl.getAttribute('datetime') : '';

                    // 互动数据
                    const likesEl = el.querySelector('[data-testid="likeCount"]');
                    tweet.likes = likesEl ? likesEl.textContent.trim() : '0';

                    const retweetsEl = el.querySelector('[data-testid="retweetCount"]');
                    tweet.retweets = retweetsEl ? retweetsEl.textContent.trim() : '0';

                    const repliesEl = el.querySelector('[data-testid="replyCount"]');
                    tweet.replies = repliesEl ? repliesEl.textContent.trim() : '0';

                    // 是否敏感内容
                    tweet.is_sensitive = el.classList.contains('with-context') &&
                        el.querySelector('[data-testid="AppTab_Sensitive"]') !== null;

                    tweets.push(tweet);
                }}

                return tweets;
            }}""")

            # 清理数据
            for t in tweets_data:
                tweets.append({
                    "text": t.get("text", ""),
                    "date": t.get("date", ""),
                    "likes": self._safe_parse_int(t.get("likes", "0")),
                    "retweets": self._safe_parse_int(t.get("retweets", "0")),
                    "replies": self._safe_parse_int(t.get("replies", "0")),
                    "is_sensitive": t.get("is_sensitive", False),
                    "is_nsfw": False  # 后续可根据内容判断
                })

        except Exception as e:
            pass  # 返回空列表

        return tweets

    async def _check_account_status(self, page):
        """检查账号状态"""
        data = {
            "account_status": "unknown",
            "is_restricted": False
        }

        try:
            # 检查页面内容判断状态
            page_content = await page.evaluate("""() => document.body.textContent""")

            if "This account's posts are visible" in page_content or "posts are visible" in page_content.lower():
                data["account_status"] = "normal"
            elif "This account is restricted" in page_content:
                data["account_status"] = "restricted"
                data["is_restricted"] = True
            elif "Suspended" in page_content or "suspended" in page_content.lower():
                data["account_status"] = "suspended"
            elif "This account is locked" in page_content:
                data["account_status"] = "locked"
            else:
                # 默认正常（页面能加载）
                data["account_status"] = "normal"

        except Exception:
            data["account_status"] = "unknown"

        return data

    def _parse_number(self, text):
        """解析带单位的数字（如 1.2K, 3.5M）"""
        if not text:
            return None
        text = text.replace(",", "").strip()
        try:
            if text.upper().endswith("K"):
                return int(float(text[:-1]) * 1000)
            elif text.upper().endswith("M"):
                return int(float(text[:-1]) * 1000000)
            else:
                return int(float(text))
        except (ValueError, IndexError):
            return None

    def _safe_parse_int(self, text):
        """安全解析整数"""
        try:
            if not text:
                return 0
            text = text.replace(",", "")
            return int(float(text))
        except (ValueError, TypeError):
            return 0


async def scrape_account(username, config):
    """便捷函数：采集单个账号数据"""
    async with XScraper(config) as scraper:
        return await scraper.scrape_account(username)
