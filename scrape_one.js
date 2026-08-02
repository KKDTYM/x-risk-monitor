const fs = require('fs');
const { chromium } = require('playwright');

(async () => {
    const cookies = JSON.parse(fs.readFileSync('conny_cookies.json', 'utf8'));
    const browser = await chromium.launch({
        headless: true,
        executablePath: 'C:\\Users\\Administrator\\AppData\\Local\\ms-playwright\\chromium-1228\\chrome-win64\\chrome.exe'
    });
    const context = await browser.newContext({
        userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
        cookies: cookies
    });
    const page = await context.newPage();

    const username = process.argv[2];
    if (!username) {
        console.error('用法: node scrape_one.js <username>');
        await browser.close();
        process.exit(1);
    }

    // 去掉 @ 前缀
    const cleanName = username.replace(/^@/, '');
    const url = 'https://x.com/' + cleanName;

    console.log('访问 ' + cleanName + ' ...');

    try {
        await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30000 });
        await page.waitForTimeout(3000);

        // 尝试点击显示敏感内容按钮
        const buttons = page.locator('button');
        const btnCount = await buttons.count();
        for (let i = 0; i < Math.min(btnCount, 5); i++) {
            const btn = buttons.nth(i);
            const text = await btn.innerText().catch(() => '');
            if (text.includes('显示') || text.includes('Show')) {
                await btn.click();
                await page.waitForTimeout(3000);
                console.log('  点击了显示敏感内容按钮');
                break;
            }
        }

        // 深度滚动抓取
        const seenUrls = new Map();

        for (let cycle = 0; cycle < 25; cycle++) {
            await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
            await page.waitForTimeout(2500);

            const tweets = await page.evaluate(() => {
                const nodes = Array.from(document.querySelectorAll('article[data-testid="tweet"]'));
                return nodes.map(n => ({
                    id: n.getAttribute('data-tweet-id') || '',
                    text: (n.querySelector('div[lang]')?.textContent || '').substring(0, 500),
                    raw: n.getAttribute('data-media') || '',
                    sensitive: n.getAttribute('data-sensitive') === 'true',
                    time: n.getAttribute('data-time') || ''
                }));
            });

            let newCount = 0;
            for (const t of tweets) {
                if (t.id && !seenUrls.has(t.id)) {
                    seenUrls.set(t.id, t);
                    newCount++;
                }
            }

            if (cycle % 5 === 0 || newCount > 0) {
                console.log('  周期' + (cycle + 1) + '：累计 ' + seenUrls.size + ' 条 (新增 ' + newCount + ')');
            }

            if (seenUrls.size >= 30 && cycle > 8) break;
        }

        console.log('最终获取 ' + seenUrls.size + ' 条推文');

        // 输出结果
        const tweetArray = Array.from(seenUrls.values()).map(t => ({
            id: t.id,
            text: t.text,
            sensitive: t.sensitive,
            time: t.time
        }));
        console.log('---TWEETS---');
        console.log(JSON.stringify(tweetArray));

        await browser.close();
    } catch (err) {
        console.error('错误: ' + err.message);
        await browser.close();
        process.exit(1);
    }
})();
