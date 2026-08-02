// Playwright 抓取 X 账号推文，区分原创和转贴
const fs = require('fs');
const { chromium } = require('playwright');

(async () => {
    const cookiesPath = 'F:\\Users\\Administrator\\Documents\\WorkBuddy\\2026-07-24-21-36-14\\conny_cookies.json';
    const cookies = JSON.parse(fs.readFileSync(cookiesPath, 'utf8'));

    const browser = await chromium.launch({
        headless: true,
        executablePath: 'C:\\Users\\Administrator\\AppData\\Local\\ms-playwright\\chromium-1228\\chrome-win64\\chrome.exe'
    });

    const context = await browser.newContext({
        userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
        cookies: cookies
    });

    const page = await context.newPage();

    const username = process.argv[2] || 'sensechiori';
    const cleanName = username.replace(/^@/, '');

    console.log('账号: @' + cleanName);
    console.log('访问主页...');

    await page.goto(`https://x.com/${cleanName}`, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await page.waitForTimeout(5000);

    // 检查是否被限流
    const pageTitle = await page.title();
    const pageUrl = page.url();
    console.log('标题:', pageTitle);
    console.log('URL:', pageUrl);

    const collectedTweets = new Map();

    // 滚动 15 个周期
    for (let cycle = 0; cycle < 15; cycle++) {
        await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
        await page.waitForTimeout(2500);

        // 提取推文（重点：区分原创和转贴）
        const newTweets = await page.evaluate((currentUser) => {
            const tweets = [];
            const articles = document.querySelectorAll('article[data-testid="tweet"]');

            articles.forEach(article => {
                try {
                    // 推文ID
                    const statusLink = article.querySelector('a[href*="/status/"]');
                    if (!statusLink) return;
                    const tweetId = statusLink.href.match(/status\/(\d+)/)?.[1];
                    if (!tweetId) return;

                    // 文本
                    const textEl = article.querySelector('[data-testid="tweetText"]');
                    const text = textEl ? textEl.innerText : '';

                    // 时间戳
                    const timeEl = article.querySelector('time');
                    const datetime = timeEl ? timeEl.getAttribute('datetime') : '';

                    // 媒体
                    const hasMedia = !!article.querySelector('[data-testid="tweetPhoto"], video');

                    // 关键：判断是否转贴
                    // 标志1: socialContext 里包含 "Reposted" 或 "转推"
                    const socialContext = article.querySelector('[data-testid="socialContext"]');
                    let isRetweet = false;
                    let isQuote = false;
                    let originalAuthor = currentUser;

                    if (socialContext) {
                        const scText = socialContext.innerText || '';
                        if (scText.includes('Reposted') || scText.includes('转推') || scText.includes('Reposts')) {
                            isRetweet = true;
                            // 提取原作者（socialContext 里会有 @username）
                            const authorLink = socialContext.querySelector('a[href*="/"]');
                            if (authorLink) {
                                const m = authorLink.href.match(/x\.com\/([A-Za-z0-9_]+)/);
                                if (m) originalAuthor = m[1];
                            }
                        }
                    }

                    // 标志2: 推文开头包含 "RT @username"（有些客户端会保留）
                    if (text.trim().startsWith('RT @')) {
                        isRetweet = true;
                        const m = text.match(/RT\s+@([A-Za-z0-9_]+)/);
                        if (m) originalAuthor = m[1];
                    }

                    // 标志3: 推文链接的用户名 != 当前账号
                    // 通过 User-Name 测试id下的链接
                    const userNameLink = article.querySelector('[data-testid="User-Name"] a');
                    if (userNameLink) {
                        const m = userNameLink.href.match(/x\.com\/([A-Za-z0-9_]+)/);
                        if (m && m[1] !== currentUser) {
                            // 链接指向其他用户，可能是转贴或对话
                            originalAuthor = m[1];
                            // 再确认 socialContext
                            if (socialContext && (socialContext.innerText || '').toLowerCase().includes('reposted')) {
                                isRetweet = true;
                            }
                        }
                    }

                    // 敏感标记
                    const isSensitive = !!article.querySelector('[data-testid="sensitiveMediaButton"]');

                    tweets.push({
                        id: tweetId,
                        text: text,
                        datetime: datetime,
                        hasMedia: hasMedia,
                        isSensitive: isSensitive,
                        isRetweet: isRetweet,
                        isQuote: isQuote,
                        originalAuthor: originalAuthor
                    });
                } catch (e) {
                    // 忽略解析错误
                }
            });

            return tweets;
        }, cleanName);

        let added = 0;
        for (const t of newTweets) {
            if (!collectedTweets.has(t.id)) {
                collectedTweets.set(t.id, t);
                added++;
            }
        }

        console.log(`周期 ${cycle + 1}: 新增 ${added}, 累计 ${collectedTweets.size} 条`);

        if (collectedTweets.size >= 30 && cycle > 3) {
            console.log('已达30条，停止滚动');
            break;
        }
    }

    console.log(`\n总计获取 ${collectedTweets.size} 条推文`);

    // 统计原创 vs 转贴
    const retweets = Array.from(collectedTweets.values()).filter(t => t.isRetweet);
    const originals = Array.from(collectedTweets.values()).filter(t => !t.isRetweet);
    console.log(`原创: ${originals.length} 条`);
    console.log(`转贴: ${retweets.length} 条`);

    // 显示转贴样本
    if (retweets.length > 0) {
        console.log('\n转贴样本（前3条）:');
        retweets.slice(0, 3).forEach(t => {
            console.log(`  - RT @${t.originalAuthor}: ${t.text.substring(0, 80)}`);
        });
    }

    // 保存原始 JSON
    const result = {
        username: cleanName,
        scraped_at: new Date().toISOString(),
        source: 'playwright_cookie_session',
        total_count: collectedTweets.size,
        original_count: originals.length,
        retweet_count: retweets.length,
        tweets: Array.from(collectedTweets.values())
    };

    const outputFile = `F:\\Users\\Administrator\\Documents\\WorkBuddy\\2026-07-24-21-36-14\\data\\${cleanName}_playwright.json`;
    fs.writeFileSync(outputFile, JSON.stringify(result, null, 2), 'utf-8');
    console.log(`\n保存: ${outputFile}`);

    await browser.close();
})();