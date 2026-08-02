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

    const username = process.argv[2] || 'sunny31059';
    const cleanName = username.replace(/^@/, '');
    const url = 'https://x.com/' + cleanName;

    console.log('访问 ' + cleanName + ' ...');

    // 捕获所有 HTML 响应
    const htmlResponses = [];
    page.on('response', async (response) => {
        const respUrl = response.url();
        if (respUrl.startsWith('https://x.com/') && respUrl.includes(cleanName)) {
            try {
                const text = await response.text();
                if (text.length > 1000) {
                    htmlResponses.push({
                        url: respUrl,
                        html: text
                    });
                    console.log('捕获 HTML: ' + respUrl + ' (' + text.length + ' bytes)');
                }
            } catch (e) {}
        }
    });

    try {
        await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30000 });
        await page.waitForTimeout(5000);

        // 滚动
        for (let cycle = 0; cycle < 15; cycle++) {
            await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
            await page.waitForTimeout(2500);
        }

        // 再次捕获
        await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30000 });
        await page.waitForTimeout(5000);
        
        for (let cycle = 0; cycle < 10; cycle++) {
            await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
            await page.waitForTimeout(2500);
        }

        // 从 HTML 中提取推文
        let tweets = [];
        for (const h of htmlResponses) {
            const extracted = extractFromHTML(h.html, cleanName);
            tweets = tweets.concat(extracted);
        }

        // 去重
        const seen = new Set();
        const deduped = [];
        for (const t of tweets) {
            if (!t.text || t.text.length < 10) continue;
            const key = t.text.substring(0, 50);
            if (!seen.has(key)) {
                seen.add(key);
                deduped.push(t);
            }
        }

        console.log('从 HTML 提取 ' + deduped.length + ' 条推文');
        console.log('---TWEETS---');
        console.log(JSON.stringify(deduped));

        await page.screenshot({ path: 'debug_' + cleanName + '.png' });
        await browser.close();
    } catch (err) {
        console.error('错误: ' + err.message);
        await browser.close();
        process.exit(1);
    }
})();

function extractFromHTML(html, username) {
    const tweets = [];
    
    // 方法 1: 查找所有包含用户推文的 JSON 嵌入数据
    // X 的 SSR HTML 中通常会嵌入 __UNIVERSAL_DATA__ 或类似数据
    const dataPatterns = [
        /__UNIVERSAL_DATA__\s*=\s*({[\s\S]*?})\s*;\s*<\/script>/,
        /"timelineEntryResult":\{[\s\S]*?"result":\{[\s\S]*?"legacy":\{[\s\S]*?"full_text":"([^"]+)"/g,
        /"full_text":"([^"]+)"/g
    ];

    // 提取所有 full_text
    const textMatches = html.match(/"full_text":"([^"]+)"/g);
    if (textMatches) {
        for (const m of textMatches) {
            const text = m.replace(/"full_text":"([^"]+)"/, '$1').replace(/\\u[\dA-F]{4}/gi, '').substring(0, 500);
            if (text.length > 5) {
                tweets.push({ text: text, source: 'full_text' });
            }
        }
    }

    // 方法 2: 查找包含用户名的推文块
    const userBlockPattern = new RegExp('{' + username + '[\\s\\S]{0,500}?"full_text":"([^"]+)"', 'g');
    const userMatches = [...html.matchAll(userBlockPattern)];
    
    for (const m of userMatches) {
        const text = m[1].replace(/\\u[\dA-F]{4}/gi, '').substring(0, 500);
        if (text.length > 5) {
            tweets.push({ text: text, source: 'user_block' });
        }
    }

    return tweets;
}
