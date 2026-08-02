
const fs = require('fs');
const { chromium } = require('playwright');

(async () => {
    const cookies = JSON.parse(fs.readFileSync(r'F:\Users\Administrator\Documents\WorkBuddy\2026-07-24-21-36-14\conny_cookies.json', 'utf8'));
    const browser = await chromium.launch({
        headless: true,
        executablePath: r'C:\Users\Administrator\AppData\Local\ms-playwright\chromium-1228\chrome-win64\chrome.exe'
    });
    const context = await browser.newContext({
        userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
        cookies: cookies
    });
    const page = await context.newPage();

    await page.goto('https://x.com/sunny31059', { waitUntil: 'domcontentloaded', timeout: 30000 });
    await page.waitForTimeout(5000);

    const html = await page.content();
    fs.writeFileSync(r'F:\Users\Administrator\Documents\WorkBuddy\2026-07-24-21-36-14\debug_sunny31059.html', html, 'utf-8');
    console.log('HTML saved: ' + html.length + ' bytes');

    await browser.close();
})();
