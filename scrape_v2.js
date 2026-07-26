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
    const url = 'https://x.com/' + cleanName + '?lang=zh-cn';

    console.log('访问 ' + cleanName + ' ...');

    try {
        // 先滚动到触发内容加载
        await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30000 });
        await page.waitForTimeout(3000);

        // 尝试点击显示敏感内容
        const buttons = page.locator('button');
        const btnCount = await buttons.count();
        for (let i = 0; i < Math.min(btnCount, 5); i++) {
            const btn = buttons.nth(i);
            const text = await btn.innerText().catch(() => '');
            if (text.includes('显示') || text.includes('Show')) {
                await btn.click();
                await page.waitForTimeout(3000);
                console.log('  点击了显示敏感内容按钮');
                break;
            }
        }

        // 深度滚动
        for (let cycle = 0; cycle < 30; cycle++) {
            await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
            await page.waitForTimeout(2500);

            // 获取所有推文容器 - 尝试多种选择器
            const tweets = await page.evaluate(() => {
                // 尝试不同的选择器
                const selectors = [
                    'article[data-testid="tweet"]',
                    'div[data-testid="tweet"]',
                    'article[data-testid="tweetCell"]',
                    'div[data-testid="tweetCell"]',
                    '[data-testid="tweet"]'
                ];

                for (const sel of selectors) {
                    const nodes = Array.from(document.querySelectorAll(sel));
                    if (nodes.length > 0) {
                        return nodes.slice(0, 50).map(n => ({
                            selector: sel,
                            text: (n.querySelector('span[lang]')?.textContent ||
                                   n.querySelector('div[dir]')?.textContent ||
                                   n.textContent || '').substring(0, 500).trim(),
                            id: n.getAttribute('data-tweet-id') || n.getAttribute('data-docid') || '',
                            sensitive: n.getAttribute('data-sensitive-content') === 'true'
                        }));
                    }
                }

                // 如果都没找到，尝试从页面文本中提取推文内容
                const bodyText = document.body.textContent;
                return [{ text: bodyText.substring(0, 2000), selector: 'bodyText', id: 'body' }];
            });

            console.log('  周期' + (cycle + 1) + '：找到 ' + tweets.length + ' 个元素');

            if (tweets.length > 0 && tweets[0].selector !== 'bodyText' && cycle > 5) {
                break;
            }
        }

        // 获取最终推文
        const finalTweets = await page.evaluate(() => {
            const nodes = Array.from(document.querySelectorAll(
                'article[data-testid="tweet"], div[data-testid="tweet"], article[data-testid="tweetCell"], div[data-testid="tweetCell"]'
            ));

            const results = nodes.slice(0, 50).map(n => {
                const textEl = n.querySelector('span[lang="zh-Hans"], span[lang="zh"], div[dir="ltr"]');
                return {
                    text: (textEl?.textContent || n.textContent || '').substring(0, 500).trim(),
                    id: n.getAttribute('data-tweet-id') || n.getAttribute('data-docid') || '',
                    sensitive: n.getAttribute('data-sensitive-content') === 'true' || n.getAttribute('data-sensitive') === 'true'
                };
            });

            // 去重
            const seen = new Set();
            return results.filter(r => {
                if (!r.text || r.text.length < 10) return false;
                if (seen.has(r.text.substring(0, 50))) return false;
                seen.add(r.text.substring(0, 50));
                return true;
            });
        });

        console.log('最终获取 ' + finalTweets.length + ' 条有效推文');
        console.log('---TWEETS---');
        console.log(JSON.stringify(finalTweets));

        // 保存原始截图
        await page.screenshot({ path: 'debug_' + cleanName + '.png' });
        console.log('截图已保存: debug_' + cleanName + '.png');

        await browser.close();
    } catch (err) {
        console.error('错误: ' + err.message);
        await browser.close();
        process.exit(1);
    }
})();
