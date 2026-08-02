// 改进版：抓所有 article + 链接
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
    await page.waitForTimeout(8000);

    // 看 article 里的内容
    const articlesInfo = await page.evaluate(() => {
        const articles = Array.from(document.querySelectorAll('article'));
        return articles.slice(0, 3).map((a, i) => {
            // 找第一个status链接
            const statusLinks = Array.from(a.querySelectorAll('a[href*="/status/"]'));
            const uniqueLinks = [...new Set(statusLinks.map(l => l.href.split('?')[0]))];

            // 找文本（尝试多种选择器）
            const textEl = a.querySelector('[data-testid="tweetText"]') || a.querySelector('div[lang]');
            const text = textEl ? (textEl.innerText || textEl.textContent).substring(0, 200) : '';

            // 找时间
            const timeEl = a.querySelector('time');
            const time = timeEl ? timeEl.getAttribute('datetime') : '';

            // 找用户名
            const userNames = Array.from(a.querySelectorAll('[data-testid="User-Name"] a')).map(l => l.href);

            return {
                i,
                uniqueLinks: uniqueLinks.slice(0, 5),
                textLen: text.length,
                text: text,
                time,
                userNames: userNames
            };
        });
    });

    console.log(JSON.stringify(articlesInfo, null, 2));

    // 看 status 链接对应的完整URL
    const allStatusLinks = await page.evaluate(() => {
        const links = Array.from(document.querySelectorAll('a[href*="/status/"]'));
        const unique = [...new Set(links.map(l => l.href.split('?')[0]))];
        return unique.slice(0, 20);
    });
    console.log('\n所有 status 链接:');
    allStatusLinks.forEach(l => console.log('  ' + l));

    await browser.close();
})();