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

    console.log('访问 ' + cleanName + ' 时间线...');
    // 直接访问时间线
    await page.goto('https://x.com/' + cleanName + '/with_replies', { waitUntil: 'domcontentloaded', timeout: 30000 });
    await page.waitForTimeout(3000);

    // 先点击"显示敏感内容"
    try {
        const buttons = await page.$$('button');
        for (const btn of buttons) {
            const txt = await btn.innerText().catch(() => '');
            if (txt.includes('显示') || txt.includes('Show')) {
                await btn.click();
                await page.waitForTimeout(3000);
                console.log('点击了显示敏感内容按钮');
                break;
            }
        }
    } catch (e) {
        console.log('敏感按钮处理: ' + e.message);
    }

    // 深度滚动 - 收集 HTML 中的 meta 标签
    const seenTexts = new Set();
    const allTweets = [];

    for (let cycle = 0; cycle < 30; cycle++) {
        await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
        await page.waitForTimeout(2000);

        // 获取当前页面的 HTML
        const html = await page.content();

        // 提取 articleBody 格式的推文
        const metaPattern = /<meta content="([^"]+)"\s+itemprop="articleBody">/g;
        let match;
        while ((match = metaPattern.exec(html)) !== null) {
            const text = match[1].trim();
            if (text.length > 10 && !seenTexts.has(text)) {
                seenTexts.add(text);
                allTweets.push(text);
            }
        }

        if (cycle % 5 === 0) {
            console.log('  周期 ' + (cycle + 1) + '：累计 ' + allTweets.length + ' 条（去重后）');
        }

        if (allTweets.length >= 30) {
            console.log('已达到30条目标');
            break;
        }
    }

    console.log('最终获取 ' + allTweets.length + ' 条推文');

    // 保存结果
    const result = {
        username: cleanName,
        scraped_at: new Date().toISOString(),
        tweets: allTweets.map((text, i) => ({
            id: i,
            text: text,
            has_image: false // 简化，后续从 HTML 额外提取
        }))
    };

    fs.writeFileSync('F:\\Users\\Administrator\\Documents\\WorkBuddy\\2026-07-24-21-36-14\\data\\' + cleanName + '_timeline.json', JSON.stringify(result, null, 2), 'utf-8');
    console.log('结果保存: data/' + cleanName + '_timeline.json');

    // 输出前3条示例
    console.log('\n前3条示例:');
    for (const t of allTweets.slice(0, 3)) {
        console.log('  - ' + t.substring(0, 100));
    }

    await browser.close();
})();
