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

    // 收集 Network 响应
    const networkTweets = [];
    const seenTweetIds = new Set();

    page.on('response', async (response) => {
        const url = response.url();
        
        // X API 返回推文数据的端点
        if (url.includes('/2/timeline/') || url.includes('/2/feed/')) {
            try {
                const json = await response.json();
                console.log('截获 API 响应: ' + url.substring(0, 100));
                
                // 解析 JSON 中的推文
                const tweets = extractTweetsFromJSON(json);
                console.log('  解析到 ' + tweets.length + ' 条推文');
                
                for (const t of tweets) {
                    if (t.id && !seenTweetIds.has(t.id)) {
                        seenTweetIds.add(t.id);
                        networkTweets.push(t);
                    }
                }
            } catch (e) {
                // 不是 JSON 响应，忽略
            }
        }
    });

    try {
        await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30000 });
        await page.waitForTimeout(5000);

        // 点击显示敏感内容
        const buttons = page.locator('button');
        const btnCount = await buttons.count();
        for (let i = 0; i < Math.min(btnCount, 10); i++) {
            try {
                const btn = buttons.nth(i);
                const text = await btn.innerText().catch(() => '');
                if (text.includes('显示') || text.includes('Show') || text.includes('Show more')) {
                    await btn.click();
                    await page.waitForTimeout(2000);
                    console.log('  点击了显示按钮');
                }
            } catch (e) {}
        }

        // 深度滚动
        for (let cycle = 0; cycle < 30; cycle++) {
            await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
            await page.waitForTimeout(3000);

            console.log('  周期' + (cycle + 1) + '：Network 获取 ' + networkTweets.length + ' 条');

            if (networkTweets.length >= 20 && cycle > 5) {
                console.log('  已达到足够推文数量，提前结束');
                break;
            }
        }

        // 兜底：DOM 解析
        let domTweets = [];
        if (networkTweets.length < 10) {
            console.log('  Network 数据不足，尝试 DOM 解析...');
            domTweets = await page.evaluate(() => {
                // 多种选择器尝试
                const selectors = [
                    'article[data-testid="tweet"]',
                    'div[data-testid="tweet"]',
                    'article[data-testid="tweetCell"]',
                    'div[data-testid="tweetCell"]'
                ];

                for (const sel of selectors) {
                    const nodes = Array.from(document.querySelectorAll(sel));
                    if (nodes.length > 0) {
                        return nodes.slice(0, 50).map(n => {
                            const textEl = n.querySelector('span[lang], div[dir="ltr"]');
                            return {
                                id: n.getAttribute('data-tweet-id') || n.getAttribute('data-docid') || '',
                                text: (textEl?.textContent || '').trim(),
                                sensitive: n.getAttribute('data-sensitive-content') === 'true' || n.getAttribute('data-sensitive') === 'true'
                            };
                        });
                    }
                }
                return [];
            });
            console.log('  DOM 解析到 ' + domTweets.length + ' 条');
        }

        // 合并去重
        const allTweets = [...networkTweets];
        for (const d of domTweets) {
            if (d.text && d.text.length > 10 && !seenTweetIds.has(d.id)) {
                allTweets.push(d);
            }
        }

        // 去重（按文本前 50 字符）
        const deduped = [];
        const textSeen = new Set();
        for (const t of allTweets) {
            if (!t.text || t.text.length < 10) continue;
            const key = t.text.substring(0, 50);
            if (!textSeen.has(key)) {
                textSeen.add(key);
                deduped.push(t);
            }
        }

        console.log('最终获取 ' + deduped.length + ' 条推文');
        console.log('---TWEETS---');
        console.log(JSON.stringify(deduped));

        // 截图
        await page.screenshot({ path: 'debug_' + cleanName + '.png' });
        console.log('截图已保存: debug_' + cleanName + '.png');

        await browser.close();
    } catch (err) {
        console.error('错误: ' + err.message);
        await browser.close();
        process.exit(1);
    }
})();

function extractTweetsFromJSON(obj, results = []) {
    if (!obj || typeof obj !== 'object') return results;

    // 递归查找 tweet 数据
    for (const key of Object.keys(obj)) {
        const val = obj[key];
        
        // 查找 items 数组中的 tweet
        if (Array.isArray(val)) {
            for (const item of val) {
                if (item && typeof item === 'object') {
                    // 检查是否包含推文内容
                    if (item.itemComponents || item.tweet_results || item.tweet_result) {
                        const tweet = parseTweetItem(item);
                        if (tweet && tweet.text) {
                            results.push(tweet);
                        }
                    }
                    // 递归查找
                    extractTweetsFromJSON(item, results);
                }
            }
        } else if (typeof val === 'object') {
            // 检查是否是直接的 tweet 对象
            if (val.itemComponents || val.tweet_results || val.tweet_result) {
                const tweet = parseTweetItem(val);
                if (tweet && tweet.text) {
                    results.push(tweet);
                }
            }
            extractTweetsFromJSON(val, results);
        }
    }

    return results;
}

function parseTweetItem(item) {
    // 获取推文 ID
    const tweetId = item?.itemContent?.tweet_results?.result?.rest_id ||
                    item?.itemContent?.tweet_result?.result?.rest_id ||
                    item?.itemResults?.tweet_results?.result?.rest_id || '';
    
    // 获取推文文本
    let text = '';
    const instructions = item?.itemContent?.tweet_results?.result?.legacy?.full_text ||
                        item?.itemContent?.tweet_result?.result?.legacy?.full_text || '';
    
    if (instructions) {
        // 解析 rich text
        text = instructions.substring(0, 500);
    }

    // 获取时间
    const createdAt = item?.itemContent?.tweet_results?.result?.legacy?.created_at ||
                      item?.itemContent?.tweet_result?.result?.legacy?.created_at || '';

    if (!text && !tweetId) return null;

    return {
        id: tweetId,
        text: text,
        time: createdAt,
        sensitive: false
    };
}
