// 深度查找"已转帖"标记
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
    await page.waitForTimeout(10000);

    // 1. 查找页面上所有含"已转帖"的文本节点
    const retweetMarkers = await page.evaluate(() => {
        const results = [];

        // 方法1: 直接查找包含"已转帖"的元素
        const allElements = document.querySelectorAll('*');
        for (const el of allElements) {
            const txt = (el.textContent || '').trim();
            if (txt === '已转帖' || txt === 'Reposted' || txt.startsWith('已转帖') || txt.startsWith('Reposted')) {
                results.push({
                    type: 'text-match',
                    tag: el.tagName,
                    testid: el.getAttribute('data-testid'),
                    text: txt.substring(0, 100),
                    parentTag: el.parentElement?.tagName,
                    parentTestid: el.parentElement?.getAttribute('data-testid')
                });
            }
        }

        // 方法2: 查找 aria-label 含 retweet/repost
        const ariaElements = document.querySelectorAll('[aria-label*="repost" i], [aria-label*="retweet" i]');
        for (const el of ariaElements) {
            results.push({
                type: 'aria-match',
                aria: el.getAttribute('aria-label'),
                tag: el.tagName
            });
        }

        // 方法3: 查找 div 中文本以"已转帖"开头
        const divs = document.querySelectorAll('div');
        for (const d of divs) {
            const t = (d.innerText || '').trim();
            if (t.includes('已转帖') || t.includes('Reposted')) {
                const childCount = d.children.length;
                if (childCount < 5) {  // 找到小的容器
                    results.push({
                        type: 'div-match',
                        childCount: childCount,
                        text: t.substring(0, 80)
                    });
                }
            }
        }

        return results.slice(0, 30);
    });

    console.log('=== 转贴标记检测结果 ===');
    console.log('找到', retweetMarkers.length, '个候选元素');
    console.log(JSON.stringify(retweetMarkers, null, 2));

    // 2. 抓取所有 article 内部完整 HTML（找转贴标记）
    const articlesHtml = await page.evaluate(() => {
        const articles = Array.from(document.querySelectorAll('article'));
        return articles.slice(0, 3).map((a, i) => {
            // 找 article 内所有 testid
            const testids = Array.from(a.querySelectorAll('[data-testid]')).map(e => e.getAttribute('data-testid')).filter((v, i, a) => a.indexOf(v) === i);
            // 找article 完整 HTML（截取前1000字）
            const html = a.outerHTML.substring(0, 2000);
            return { i, testids, htmlPreview: html };
        });
    });

    console.log('\n=== Article 内部 testid 列表 ===');
    articlesHtml.forEach(a => {
        console.log(`\n[Article ${a.i}] testids:`, a.testids);
    });

    await browser.close();
})();