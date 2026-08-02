// 滚动抓取所有 status 链接（增量收集）
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

    // 收集所有 status 链接
    const allIds = new Map();

    for (let cycle = 0; cycle < 20; cycle++) {
        await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
        await page.waitForTimeout(2500);

        const links = await page.evaluate(() => {
            const anchors = document.querySelectorAll('a[href*="/status/"]');
            const ids = new Map();
            anchors.forEach(a => {
                const m = a.href.match(/status\/(\d+)/);
                if (m) {
                    const id = m[1];
                    if (!ids.has(id)) {
                        // 提取 /status/ID/photo/N 这种是图片附件链接，跳过
                        // 但我们需要记录完整链接（包括 /photo/、/video/）
                        // 提取原始推文作者
                        const authorM = a.href.match(/x\.com\/([A-Za-z0-9_]+)\/status/);
                        const author = authorM ? authorM[1] : '';
                        ids.set(id, {
                            id: id,
                            author: author,
                            url: a.href
                        });
                    }
                }
            });
            return Array.from(ids.entries());
        });

        let added = 0;
        for (const [id, info] of links) {
            if (!allIds.has(id)) {
                allIds.set(id, info);
                added++;
            }
        }

        if (cycle % 3 === 0) {
            console.log(`周期 ${cycle + 1}: 本轮 ${links.length} 个ID，新增 ${added}，累计 ${allIds.size}`);
        }

        if (allIds.size >= 50) {
            console.log('已达50条，停止');
            break;
        }
    }

    console.log(`\n总计 ${allIds.size} 个唯一推文ID`);

    // 分析：哪些是本人发的，哪些是转贴
    const ids = Array.from(allIds.values());
    const selfTweets = ids.filter(t => t.author === 'sensechiori');
    const othersTweets = ids.filter(t => t.author !== 'sensechiori' && t.author !== '');

    console.log(`本人原创: ${selfTweets.length}`);
    console.log(`他人推文（可能是转贴）: ${othersTweets.length}`);

    if (othersTweets.length > 0) {
        console.log('\n其他作者推文:');
        othersTweets.slice(0, 10).forEach(t => console.log(`  @${t.author}: https://x.com/${t.author}/status/${t.id}`));
    }

    // 保存 ID 列表
    fs.writeFileSync(
        'F:\\Users\\Administrator\\Documents\\WorkBuddy\\2026-07-24-21-36-14\\data\\sensechiori_status_ids.json',
        JSON.stringify(Array.from(allIds.values()), null, 2),
        'utf-8'
    );
    console.log(`\n保存: data/sensechiori_status_ids.json`);

    await browser.close();
})();