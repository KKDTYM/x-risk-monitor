// Playwright深度滚动抓取 - 用a[href*="/status/"]提取
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

    const username = process.argv[2] || 'sunny31059';
    const cleanName = username.replace(/^@/, '');

    console.log(`访问 @${cleanName}...`);

    await page.goto(`https://x.com/${cleanName}`, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await page.waitForTimeout(5000);

    const collectedTweets = new Map();

    for (let cycle = 0; cycle < 25; cycle++) {
        // 提取当前DOM中所有 /status/ 链接
        const links = await page.evaluate(() => {
            const anchors = document.querySelectorAll('a[href*="/status/"]');
            const ids = new Set();
            anchors.forEach(a => {
                const match = a.href.match(/status\/(\d+)/);
                if (match) ids.add(match[1]);
            });
            return Array.from(ids);
        });

        let added = 0;
        for (const id of links) {
            if (!collectedTweets.has(id)) {
                collectedTweets.set(id, { id, text: '', datetime: '', hasMedia: false, isSensitive: false });
                added++;
            }
        }

        if (cycle % 5 === 0) {
            console.log(`  周期 ${cycle + 1}: 新增 ${added}, 累计 ${collectedTweets.size} 条`);
        }

        // 滚动
        await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
        await page.waitForTimeout(2000);

        if (collectedTweets.size >= 30 && cycle > 3) {
            console.log(`已达30条，停止`);
            break;
        }
    }

    console.log(`\n累计推文ID: ${collectedTweets.size} 条`);

    // 对每个ID用Fxtwitter API拉详情
    console.log('\n用Fxtwitter API拉详情...');
    const axios = require('https');
    const https = require('https');

    let success = 0, failed = 0;
    for (const [id, tweet] of collectedTweets) {
        const url = `https://api.fxtwitter.com/${cleanName}/status/${id}`;
        try {
            const data = await new Promise((resolve, reject) => {
                https.get(url, { headers: { 'User-Agent': 'Mozilla/5.0' } }, (res) => {
                    let body = '';
                    res.on('data', chunk => body += chunk);
                    res.on('end', () => {
                        try {
                            resolve(JSON.parse(body));
                        } catch (e) {
                            reject(e);
                        }
                    });
                }).on('error', reject);
            });

            if (data.code === 200 && data.tweet) {
                tweet.text = data.tweet.text || '';
                tweet.datetime = data.tweet.created_at || '';
                tweet.hasMedia = (data.tweet.media?.all?.length || 0) > 0;
                tweet.isSensitive = data.tweet.possibly_sensitive || false;
                success++;
            } else {
                failed++;
            }
        } catch (e) {
            failed++;
        }

        // 控制速率避免限流
        await new Promise(r => setTimeout(r, 500));

        if (success >= 30) break;
    }

    console.log(`\n成功 ${success}, 失败 ${failed}`);

    // 保存结果
    const result = {
        username: cleanName,
        scraped_at: new Date().toISOString(),
        source: 'playwright_dom+fxtwitter_api',
        profile: {},
        recent_tweets: Array.from(collectedTweets.values())
            .filter(t => t.text)
            .map(t => ({
                text: t.text,
                date: t.datetime,
                tweet_id: t.id,
                is_sensitive: t.isSensitive,
                has_image: t.hasMedia,
                raw: ''
            }))
    };

    fs.writeFileSync(
        `F:\\Users\\Administrator\\Documents\\WorkBuddy\\2026-07-24-21-36-14\\data\\${cleanName}_timeline_v3.json`,
        JSON.stringify(result, null, 2),
        'utf-8'
    );
    console.log(`保存: data/${cleanName}_timeline_v3.json (${result.recent_tweets.length} 条带文本)`);

    await browser.close();
})();