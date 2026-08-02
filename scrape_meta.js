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

    try {
        // 先访问主页获取个人主页 HTML
        await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30000 });
        await page.waitForTimeout(5000);

        // 获取完整 HTML
        const html = await page.content();
        
        // 提取所有 meta[articleBody/text/headline]
        const tweets = [];
        const tweetRegex = /<meta[^>]*itemprop="(articleBody|text|headline)"[^>]*content="([^"]+)"[^>]*>/gi;
        let match;
        
        const seenTexts = new Set();
        
        while ((match = tweetRegex.exec(html)) !== null) {
            const type = match[1];
            const content = match[2].trim();
            
            if (content.length < 10 || seenTexts.has(content.substring(0, 50))) continue;
            seenTexts.add(content.substring(0, 50));
            
            // 提取 URL（如果有）
            const urlMatch = html.substring(match.index).match(/itemprop="url"[^>]*content="([^"]+)"/);
            const tweetUrl = urlMatch ? urlMatch[1] : '';
            
            // 提取日期
            const dateMatch = html.substring(match.index).match(/itemprop="datePublished"[^>]*content="([^"]+)"/);
            const datePublished = dateMatch ? dateMatch[1] : '';
            
            // 提取图片
            const imgMatch = html.substring(match.index).match(/itemprop="image"[^>]*content="([^"]+)"/);
            const imageUrl = imgMatch ? imgMatch[1] : '';
            
            tweets.push({
                text: content.replace(/\\n/g, '\n').substring(0, 500),
                url: tweetUrl,
                date: datePublished,
                has_image: !!imageUrl,
                image_url: imageUrl,
                source: type
            });
        }

        console.log('从 meta 标签提取 ' + tweets.length + ' 条推文');
        
        // 去重（按文本）
        const deduped = [];
        const textSeen = new Set();
        for (const t of tweets) {
            if (!t.text || t.text.length < 10) continue;
            const key = t.text.substring(0, 50);
            if (!textSeen.has(key)) {
                textSeen.add(key);
                deduped.push(t);
            }
        }

        console.log('去重后 ' + deduped.length + ' 条');
        console.log('---TWEETS---');
        console.log(JSON.stringify(deduped, null, 2));

        await page.screenshot({ path: 'debug_' + cleanName + '.png' });
        await browser.close();
    } catch (err) {
        console.error('错误: ' + err.message);
        await browser.close();
        process.exit(1);
    }
})();
