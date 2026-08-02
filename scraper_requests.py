"""
X 账号数据采集 — requests + Playwright 混合版本
- Profile 数据：通过 fxtwitter API 获取（纯 requests，快速）
- 推文内容：通过 Playwright 抓取 fxtwitter 页面（可靠）
"""

import requests
import json
import logging
import re
from datetime import datetime
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class XScraperRequests:
    """requests + Playwright 混合版本的 X 数据采集器"""

    BASE_URL = "https://api.fxtwitter.com"

    def __init__(self, config=None):
        self.config = config or {}
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.9,zh-CN,zh;q=0.8",
        })

        proxy = self.config.get("proxy", {})
        if proxy.get("enabled"):
            proxy_url = f"http://{proxy.get('socks5_host')}:{proxy.get('socks5_port')}"
            self.session.proxies = {"http": proxy_url, "https": proxy_url}
            logger.info(f"Proxy enabled: {proxy_url}")
        else:
            self.session.proxies = {}
            logger.info("No proxy, direct connection")
        
        # Playwright 浏览器实例（用于获取推文内容）
        self._browser = None
        self._page = None

    def _get_browser(self):
        """懒加载 Playwright 浏览器"""
        if self._page is None:
            try:
                from playwright.sync_api import sync_playwright
                p = sync_playwright().start()
                self._browser = p.chromium.launch(headless=True)
                self._page = self._browser.new_page()
                logger.info("Playwright browser launched")
            except Exception as e:
                logger.warning(f"Playwright launch failed: {e}")
                self._browser = None
        return self._page

    def scrape_account(self, username):
        """采集单个账号的完整数据"""
        username = username.lstrip("@")
        logger.info(f"Scraping @{username}...")

        result = {
            "username": username,
            "scraped_at": datetime.now().isoformat(),
            "profile": None,
            "recent_tweets": [],
            "tweets_note": "",
            "account_status": {
                "is_protected": False,
                "is_suspended": False,
                "is_frozen": False,
            },
        }

        try:
            profile = self._fetch_profile(username)
            result["profile"] = profile
            logger.info(f"Profile fetched for @{username}")
        except Exception as e:
            logger.error(f"Failed profile for @{username}: {e}")
            result["error"] = str(e)
            return result

        # 获取推文内容（最近 30 篇，包括转发）
        try:
            tweets = self._fetch_tweets(username, count=30)
            result["recent_tweets"] = tweets[:30]
            if not tweets:
                result["tweets_note"] = "未获取到推文内容"
            else:
                result["tweets_note"] = f"成功获取 {len(tweets)} 篇推文"
        except Exception as e:
            logger.warning(f"Failed to fetch tweets for @{username}: {e}")
            result["tweets_note"] = "推文获取失败"

        # 账号状态
        profile = result["profile"]
        if profile:
            result["account_status"]["is_protected"] = profile.get("protected", False)
            if not profile.get("avatar_url") and not profile.get("description"):
                result["account_status"]["is_suspended"] = True

        return result

    def _fetch_profile(self, username):
        """通过 fxtwitter API 获取 profile"""
        url = f"{self.BASE_URL}/{username}"
        resp = self.session.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        if data.get("code") != 200:
            raise ValueError(f"fxtwitter API error: {data.get('message')}")

        user = data.get("user", {})
        if not user:
            raise ValueError(f"No user data for @{username}")

        return {
            "screen_name": user.get("screen_name"),
            "name": user.get("name"),
            "description": user.get("description", ""),
            "location": user.get("location", ""),
            "followers_count": user.get("followers", 0),
            "following_count": user.get("following", 0),
            "tweet_count": user.get("tweets", 0),
            "likes_count": user.get("likes", 0),
            "media_count": user.get("media_count", 0),
            "profile_image_url": user.get("avatar_url", ""),
            "banner_url": user.get("banner_url", ""),
            "protected": user.get("protected", False),
            "verified": user.get("verification", {}).get("verified", False),
            "created_at": user.get("joined"),
            "user_id": user.get("id", ""),
        }

    def _fetch_tweets(self, username: str, count: int = 10) -> List[Dict]:
        """通过 fxtwitter API v2 获取用户最近推文（包括转发）"""
        tweets = []
        username_clean = username.lstrip("@").lower()
        
        try:
            # 1. 尝试使用 fxtwitter v2 profile statuses API 
            api_url = f"https://api.fxtwitter.com/2/profile/{username}/statuses"
            logger.info(f"Fetching profile tweets from {api_url}")
            
            resp = self.session.get(api_url, timeout=20)
            if resp.status_code == 200:
                data = resp.json()
                results = data.get("results", [])
                logger.info(f"Got {len(results)} tweets from FxTwitter v2 API for @{username}")
                
                for item in results[:count]:
                    if item.get("type") != "status":
                        continue
                        
                    author = item.get("author", {})
                    author_screen_name = author.get("screen_name", "").lower()
                    
                    # 判断类型是否为转发 (检查 reposted_by, 或者原作者 screen_name 不是当前账号)
                    is_retweet = False
                    if item.get("reposted_by") is not None:
                        is_retweet = True
                    elif author_screen_name and author_screen_name != username_clean:
                        is_retweet = True
                        
                    tweets.append({
                        "id": item.get("id", ""),
                        "url": item.get("url", f"https://x.com/{username}/status/{item.get('id', '')}"),
                        "text": item.get("text", ""),
                        "is_retweet": is_retweet,
                        "created_at": item.get("created_at", ""),
                        "likes": item.get("likes", 0),
                        "retweets": item.get("reposts", 0),
                        "replies": item.get("replies", 0),
                        "possibly_sensitive": item.get("possibly_sensitive", False),
                        "original_author": author.get("screen_name", ""),
                    })
            else:
                logger.warning(f"FxTwitter v2 API returned status {resp.status_code} for @{username}")
                    
            # 2. 如果 v2 API 没拿到推文，使用 profile 中的 description 作为备用展示
            if not tweets:
                # 获取简介
                profile = self._fetch_profile(username)
                description = profile.get("description", "") if profile else ""
                if description:
                    tweets.append({
                        "text": f"[个人简介] {description[:300]}",
                        "url": f"https://x.com/{username}",
                        "is_retweet": False,
                        "created_at": "",
                        "id": "bio",
                        "likes": 0,
                        "retweets": 0,
                        "replies": 0,
                        "possibly_sensitive": False,
                        "original_author": username,
                    })
                    logger.info(f"Using description as fallback for @{username}")
            
            logger.info(f"Final tweet count for @{username}: {len(tweets)}")
                
        except Exception as e:
            logger.error(f"Error fetching tweets for @{username} via v2 API: {e}")
            
        return tweets[:count]

    def stop(self):
        """清理资源"""
        if self.session:
            self.session.close()
        if self._page:
            try:
                self._browser.close()
            except:
                pass
