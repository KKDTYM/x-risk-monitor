const fs = require('fs');
const { chromium } = require('playwright');

(async () => {
    const cookies = JSON.parse(fs.readFileSync('conny_cookies.json', 'utf8'));
    const browser = await chromium.launch({ headless: false });
    const context = await browser.newContext({
        userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
        cookies: cookies
    });
    const page = await context.newPage();

    const cleanName = 'sunny31059';
    console.log('访问 https://x.com/' + cleanName);

    try {
        await page.goto('https://x.com/' + cleanName, { waitUntil: 'domcontentloaded', timeout: 30000 });
        await page.waitForTimeout(5000);

        // 截图
        await page.screenshot({ path: 'debug_sunny1.png', fullPage: false });

        // 尝试展开敏感内容
        const buttons = page.locator('button');
        const btnCount = await buttons.count();
        console.log('按钮数量: ' + btnCount);
        for (let i = 0; i < Math.min(btnCount, 10); i++) {
            const btn = buttons.nth(i);
            const text = await btn.innerText().catch(() => '');
            const cls = await btn.evaluate(el => el.className).catch(() => '');
            if (text || cls) {
                console.log('按钮' + i + ': text=' + text.substring(0, 50) + ', class=' + cls.substring(0, 80));
            }
        }

        // 点击显示敏感内容
        const showBtn = page.locator('button').first();
        const showText = await showBtn.innerText().catch(() => '');
        console.log('首个按钮文本: ' + showText);
        if (showText.includes('显示') || showText.includes('Show') || showText.includes('Sensitive')) {
            await showBtn.click();
            await page.waitForTimeout(3000);
            await page.screenshot({ path: 'debug_sunny2.png', fullPage: false });
            console.log('已点击显示按钮');
        }

        // 再次滚动尝试加载推文
        for (let i = 0; i < 5; i++) {
            await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
            await page.waitForTimeout(2000);
        }

        // 截图看看
        await page.screenshot({ path: 'debug_sunny3.png', fullPage: false });

        // 检查页面内容
        const pageContent = await page.content();
        const tweetCount = (pageContent.match(/article\[data-testid/ig) || []).length;
        const bodyText = await page.evaluate(() => document.body?.textContent?.substring(0, 2000) || '');
        console.log('页面中 article 数量: ' + tweetCount);
        console.log('页面文本前 500: ' + bodyText.substring(0, 500));

        // 截图
        await page.screenshot({ path: 'debug_sunny4.png', fullPage: false });

        await browser.close();
    } catch (err) {
        console.error('错误: ' + err.message);
        await browser.close();
    }
})();
