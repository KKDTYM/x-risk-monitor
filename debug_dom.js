// 调试 X 主页 DOM 结构
const fs = require('fs');
const { chromium } = require('playwright');

(async () => {
    const cookies = JSON.parse(fs.readFileSync('F:\\Users\\Administrator\\Documents\\WorkBuddy\\2026-07-24-21-36-14\\conny_cookies.json', 'utf8'));
    const browser = await chromium.launch({
        headless: true,
        executablePath: 'C:\\Users\\Administrator\\AppData\\Local\\ms-playwright\\chromium-1228\\chrome-win64\\chrome.exe'
    });
    const context = await browser.newContext({
        userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        cookies: cookies
    });
    const page = await context.newPage();

    await page.goto('https://x.com/sensechiori', { waitUntil: 'domcontentloaded', timeout: 30000 });
    await page.waitForTimeout(5000);

    const info = await page.evaluate(() => {
        return {
            articles: document.querySelectorAll('article').length,
            articleTestid: document.querySelectorAll('article[data-testid="tweet"]').length,
            statusLinks: document.querySelectorAll('a[href*="/status/"]').length,
            socialContext: document.querySelectorAll('[data-testid="socialContext"]').length,
            userNames: document.querySelectorAll('[data-testid="User-Name"]').length,
            tweetTexts: document.querySelectorAll('[data-testid="tweetText"]').length,
            bodyTextLen: document.body.innerText.length,
            title: document.title,
            sampleLink: (document.querySelector('a[href*="/status/"]') || {}).href,
            firstStatusHrefs: Array.from(document.querySelectorAll('a[href*="/status/"]')).slice(0, 5).map(a => a.href)
        };
    });

    console.log(JSON.stringify(info, null, 2));

    // 保存完整HTML用于分析
    const html = await page.content();
    fs.writeFileSync('F:\\Users\\Administrator\\Documents\\WorkBuddy\\2026-07-24-21-36-14\\data\\html_sensechiori_pw.html', html, 'utf-8');
    console.log('HTML保存:', html.length, 'bytes');

    await browser.close();
})();