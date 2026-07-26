const fs = require('fs');
const { chromium } = require('playwright');

(async () => {
    const cookies = JSON.parse(fs.readFileSync('conny_cookies.json', 'utf8'));
    const browser = await chromium.launch({
        headless: false,
        executablePath: 'C:\\Users\\Administrator\\AppData\\Local\\ms-playwright\\chromium-1228\\chrome-win64\\chrome.exe'
    });
    const context = await browser.newContext({
        userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
        cookies: cookies
    });
    const page = await context.newPage();

    const username = 'sunny31059';
    const url = 'https://x.com/' + username;

    console.log('访问 ' + username + ' ...');

    await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await page.waitForTimeout(5000);

    // 截图
    await page.screenshot({ path: 'debug_sunny_v2.png' });
    console.log('截图已保存: debug_sunny_v2.png');

    // 获取页面标题和URL
    console.log('Page title: ' + await page.title());
    console.log('Current URL: ' + page.url());

    // 尝试获取页面文本
    const bodyText = await page.evaluate(() => document.body.textContent.substring(0, 2000));
    console.log('Body text (first 2000 chars): ' + bodyText);

    // 检查 article 数量
    const articleCount = await page.evaluate(() => document.querySelectorAll('article[data-testid="tweet"]').length);
    console.log('Article count: ' + articleCount);

    // 检查是否有错误消息
    const errorText = await page.evaluate(() => {
        const els = document.querySelectorAll('[data-testid="primaryColumn"]');
        return Array.from(els).map(e => e.textContent.substring(0, 500));
    });
    console.log('Primary column: ' + JSON.stringify(errorText));

    await browser.close();
})();
