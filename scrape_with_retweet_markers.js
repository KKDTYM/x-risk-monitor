// Playwright 抓取 X 账号推文 + 识别"已转帖"标记
// 方案：先用主页抓 status 链接列表，再逐个访问提取详情
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

    // 第1步：访问主页，抓 status 链接列表
    await page.goto(`https://x.com/${cleanName}`, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await page.waitForTimeout(3000);

    const statusLinks = await page.evaluate((currentUser) => {
        const links = [];
        const anchors = document.querySelectorAll('a[href*="/status/"]');
        anchors.forEach(a => {
            const m = a.href.match(/status\/(\d+)/);
            if (m) {
                links.push({ id: m[1], url: a.href });
            }
        });
        return links;
    }, cleanName);

    console.log(`主页抓取到 ${statusLinks.length} 条 status 链接`);

    // 去重
    const uniqueStatuses = [...new Map(statusLinks.map(item => [item.id, item])).values()];
    console.log(`去重后 ${uniqueStatuses.length} 条唯一推文`);

    // 第2步：对每条推文，访问并提取"已转帖"标记
    // 限制处理条数（避免太长）
    const maxProcess = Math.min(uniqueStatuses.length, 30);
    console.log(`开始逐个访问前 ${maxProcess} 条推文...`);

    const tweets = [];

    for (let i = 0; i < maxProcess; i++) {
        const status = uniqueStatuses[i];
        console.log(`[${i + 1}/${maxProcess}] 访问推文 ${status.id}...`);

        try {
            await page.goto(`https://x.com/${cleanName}/status/${status.id}`, { waitUntil: 'domcontentloaded', timeout: 15000 });
            await page.waitForTimeout(2000);

            const tweetData = await page.evaluate((currentUser) => {
                // 找所有 article 元素
                const articles = document.querySelectorAll('article');
                
                let isRetweet = false;
                let retweetAuthor = currentUser;
                let originalText = '';
                let datetime = '';
                let hasMedia = false;
                let isSensitive = false;

                articles.forEach(article => {
                    // 检查"已转帖"标记（纯文本搜索）
                    const articleText = article.innerText || '';
                    if (articleText.includes('已转帖') || articleText.includes('Reposted') || articleText.includes('Reposts')) {
                        isRetweet = true;
                        // 提取原作者名
                        const userLinks = article.querySelectorAll('a[href*="/"]');
                        userLinks.forEach(link => {
                            const href = link.href || '';
                            const m = href.match(/x\.com\/([A-Za-z0-9_\-]+)/);
                            if (m && m[1] !== currentUser) {
                                retweetAuthor = m[1];
                            }
                        });
                    }

                    // 推文正文
                    const textEl = article.querySelector('[data-testid="tweetText"], [data-testid="tweetContent"]');
                    if (textEl && !originalText) {
                        originalText = textEl.innerText || '';
                    }

                    // 时间戳
                    const timeEl = article.querySelector('time');
                    if (timeEl) {
                        datetime = timeEl.getAttribute('datetime') || '';
                    }

                    // 媒体
                    if (article.querySelector('[data-testid="tweetPhoto"], [data-testid="tweetVideo"], video, img')) {
                        hasMedia = true;
                    }

                    // 敏感标记
                    if (article.querySelector('[data-testid="sensitiveMediaButton"]')) {
                        isSensitive = true;
                    }
                });

                // 如果没找到 article，尝试从 meta 标签提取
                if (!isRetweet && !originalText) {
                    const metaDesc = document.querySelector('meta[name="description"]');
                    if (metaDesc) {
                        originalText = metaDesc.getAttribute('content') || '';
                    }
                }

                return {
                    isRetweet,
                    retweetAuthor,
                    text: originalText,
                    datetime,
                    hasMedia,
                    isSensitive
                };
            }, cleanName);

            tweets.push({
                id: status.id,
                text: tweetData.text || '',
                datetime: tweetData.datetime || '',
                isRetweet: tweetData.isRetweet,
                retweetAuthor: tweetData.retweetAuthor || cleanName,
                hasMedia: tweetData.hasMedia,
                isSensitive: tweetData.isSensitive,
                source: 'playwright_individual'
            });
        } catch (e) {
            console.log(`  [错误] 访问 ${status.id} 失败: ${e.message}`);
            // 即使失败也记录一条基础数据
            tweets.push({
                id: status.id,
                text: '',
                datetime: '',
                isRetweet: false,
                retweetAuthor: cleanName,
                hasMedia: false,
                isSensitive: false,
                source: 'playwright_failed',
                error: e.message
            });
        }
    }

    // 统计
    const retweets = tweets.filter(t => t.isRetweet);
    const originals = tweets.filter(t => !t.isRetweet);
    console.log(`\n=== 统计 ===`);
    console.log(`处理 ${tweets.length} 条推文`);
    console.log(`原创: ${originals.length} 条`);
    console.log(`转贴: ${retweets.length} 条`);

    if (retweets.length > 0) {
        console.log(`\n转贴样本（前3条）:`);
        retweets.slice(0, 3).forEach(t => {
            console.log(`  - 转 @${t.retweetAuthor}: ${t.text.substring(0, 60)}`);
        });
    }

    // 保存
    const result = {
        username: cleanName,
        scraped_at: new Date().toISOString(),
        source: 'playwright_retweet_markers',
        total_count: tweets.length,
        original_count: originals.length,
        retweet_count: retweets.length,
        tweets: tweets
    };

    const outputFile = `F:\\Users\\Administrator\\Documents\\WorkBuddy\\2026-07-24-21-36-14\\data\\${cleanName}_playwright_v2.json`;
    fs.writeFileSync(outputFile, JSON.stringify(result, null, 2), 'utf-8');
    console.log(`\n保存: ${outputFile}`);

    await browser.close();
})();
