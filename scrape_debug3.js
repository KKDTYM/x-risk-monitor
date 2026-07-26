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

    const username = 'sunny31059';
    const url = 'https://x.com/' + username;

    console.log('访问 ' + username + ' ...');

    // 收集所有网络响应
    const responses = [];
    page.on('response', async (response) => {
        const respUrl = response.url();
        
        // 只记录包含 JSON 或推文的响应
        if (respUrl.includes('tweet') || respUrl.includes('timeline') || respUrl.includes('/2/') || respUrl.includes('graphql')) {
            try {
                const contentType = response.headers()['content-type'] || '';
                if (contentType.includes('json')) {
                    const json = await response.json().catch(() => null);
                    responses.push({
                        url: respUrl.substring(0, 150),
                        status: response.status(),
                        json_preview: JSON.stringify(json).substring(0, 500)
                    });
                    console.log('JSON 响应: ' + respUrl.substring(0, 100) + ' [' + response.status() + ']');
                }
            } catch (e) {}
        }
        
        // 也记录 HTML 响应
        if (respUrl.startsWith('https://x.com/') && respUrl.includes(username)) {
            try {
                const text = await response.text().catch(() => '');
                if (text.includes('tweet') || text.includes('Tweet')) {
                    responses.push({
                        url: respUrl.substring(0, 150),
                        status: response.status(),
                        html_preview: text.substring(0, 500)
                    });
                    console.log('HTML 响应 (含 tweet): ' + respUrl.substring(0, 100) + ' [' + response.status() + ']');
                }
            } catch (e) {}
        }
    });

    try {
        await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30000 });
        await page.waitForTimeout(5000);

        // 截图
        await page.screenshot({ path: 'debug_' + username + '_v3.png' });
        console.log('截图已保存');

        // 输出所有响应
        console.log('---RESPONSES---');
        console.log(JSON.stringify(responses, null, 2));

        await browser.close();
    } catch (err) {
        console.error('错误: ' + err.message);
        await browser.close();
        process.exit(1);
    }
})();
