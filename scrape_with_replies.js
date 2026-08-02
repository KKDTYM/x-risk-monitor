// Playwright深度滚动抓取时间线 - 增量收集DOM
const fs = require('fs');
const { chromium } = require('playwright');

(async () => {
    const cookies = JSON.parse(fs.readFileSync('F:\\Users\\Administrator\\Documents\\WorkBuddy\\2026-07-24-21-36-14\\conny_cookies.json', 'utf8'));
    const browser = await chromium.launch({
        headless: true,
        executablePath: 'C:\\Users\\Administrator\\AppData\\Local\\ms-playwright\\chromium-1228\\chrome-win64\\chrome.exe'
    });
    const context = await browser.newContext({
        userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
        cookies: cookies
    });
    const page = await context.newPage();

    const username = process.argv[2] || 'shutiaoniang';
    const cleanName = username.replace(/^@/, '');

    console.log(`访问 @${cleanName} 时间线（深度滚动）...`);

    // 访问用户的"with_replies"时间线页面
    await page.goto(`https://x.com/${cleanName}/with_replies`, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await page.waitForTimeout(5000);

    // 收集推文的容器（用Map做去重）
    const collectedTweets = new Map();

    // 深度滚动 20 个周期
    for (let cycle = 0; cycle < 20; cycle++) {
        // 在每次滚动后提取当前可见的所有推文
        const newTweets = await page.evaluate(() => {
            const tweets = [];
            // 找所有 article[data-testid="tweet"]
            const articles = document.querySelectorAll('article[data-testid="tweet"]');
            articles.forEach(article => {
                try {
                    // 推文ID从status链接提取
                    const statusLink = article.querySelector('a[href*="/status/"]');
                    if (!statusLink) return;
                    const tweetId = statusLink.href.match(/status\/(\d+)/)?.[1];
                    if (!tweetId) return;

                    // 文本内容
                    const textEl = article.querySelector('[data-testid="tweetText"]');
                    const text = textEl ? textEl.innerText : '';

                    // 时间戳
                    const timeEl = article.querySelector('time');
                    const datetime = timeEl ? timeEl.getAttribute('datetime') : '';

                    // 是否有媒体
                    const hasMedia = !!article.querySelector('[data-testid="tweetPhoto"], video');

                    // 是否标记Sensitive
                    const isSensitive = !!article.querySelector('[data-testid="sensitiveMediaButton"], [aria-label*="sensitive" i]');

                    tweets.push({
                        id: tweetId,
                        text: text,
                        datetime: datetime,
                        hasMedia: hasMedia,
                        isSensitive: isSensitive
                    });
                } catch (e) {
                    // 忽略单个推文解析错误
                }
            });
            return tweets;
        });

        // 增量去重
        let added = 0;
        for (const t of newTweets) {
            if (!collectedTweets.has(t.id)) {
                collectedTweets.set(t.id, t);
                added++;
            }
        }

        if (cycle % 3 === 0) {
            console.log(`  周期 ${cycle + 1}: 本轮新增 ${added}，累计 ${collectedTweets.size} 条`);
        }

        // 滚动到底部
        await page.evaluate(() => {
            window.scrollTo(0, document.body.scrollHeight);
        });
        await page.waitForTimeout(2500);

        // 如果已经收集到30条，停止
        if (collectedTweets.size >= 30) {
            console.log(`已达到目标30条，停止滚动`);
            break;
        }
    }

    console.log(`\n最终获取 ${collectedTweets.size} 条推文`);

    // 保存结果
    const result = {
        username: cleanName,
        scraped_at: new Date().toISOString(),
        source: 'playwright_dom_parsing',
        profile: {},
        recent_tweets: Array.from(collectedTweets.values()).map(t => ({
            text: t.text,
            date: t.datetime,
            tweet_id: t.id,
            is_sensitive: t.isSensitive,
            has_image: t.hasMedia,
            raw: ''
        }))
    };

    fs.writeFileSync(
        `F:\\Users\\Administrator\\Documents\\WorkBuddy\\2026-07-24-21-36-14\\data\\${cleanName}_timeline_v2.json`,
        JSON.stringify(result, null, 2),
        'utf-8'
    );
    console.log(`结果保存: data/${cleanName}_timeline_v2.json`);

    // 显示前3条
    const tweets = Array.from(collectedTweets.values());
    console.log('\n前3条推文:');
    for (const t of tweets.slice(0, 3)) {
        console.log(`  [${t.id}] ${t.text.substring(0, 100)}`);
    }

    await browser.close();
})();