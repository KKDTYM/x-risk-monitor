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

    const username = process.argv[2] || 'shutiaoniang';
    const cleanName = username.replace(/^@/, '');

    console.log('访问 ' + cleanName + '（Network监听模式）...');

    const capturedResponses = [];

    // 监听所有网络响应
    page.on('response', async (response) => {
        const url = response.url();
        // X的API端点
        if (url.includes('/i/api/') || url.includes('/2/')) {
            try {
                const contentType = response.headers()['content-type'] || '';
                if (contentType.includes('json') || url.includes('.json')) {
                    const body = await response.text().catch(() => '');
                    if (body.length > 100) {
                        capturedResponses.push({
                            url: url,
                            status: response.status(),
                            body: body,
                            headers: response.headers()
                        });
                    }
                }
            } catch (e) {
                // 忽略错误
            }
        }
    });

    // 访问用户主页
    await page.goto('https://x.com/' + cleanName, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await page.waitForTimeout(5000);

    // 滚动页面触发更多请求
    for (let i = 0; i < 10; i++) {
        await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
        await page.waitForTimeout(2000);
    }

    console.log('捕获到 ' + capturedResponses.length + ' 个网络响应');

    // 保存所有响应
    fs.writeFileSync(
        'F:\\Users\\Administrator\\Documents\\WorkBuddy\\2026-07-24-21-36-14\\data\\' + cleanName + '_network.json',
        JSON.stringify(capturedResponses, null, 2),
        'utf-8'
    );
    console.log('响应数据保存: data/' + cleanName + '_network.json');

    // 显示URL列表
    console.log('\n捕获的URL:');
    for (const r of capturedResponses.slice(0, 10)) {
        console.log('  ' + r.url);
    }

    await browser.close();
})();
