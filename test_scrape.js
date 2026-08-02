const { chromium } = require('playwright');
const fs = require('fs');

const WS = 'F:/Users/Administrator/Documents/WorkBuddy/2026-07-24-21-36-14';

(async () => {
  const raw = JSON.parse(fs.readFileSync(`${WS}/conny_cookies.json`, 'utf8'));
  const cookies = raw.map(c => ({
    name: c.name, value: c.value, domain: c.domain, path: c.path || '/',
    expires: c.expirationDate ? Math.floor(c.expirationDate) : undefined,
    httpOnly: c.httpOnly, secure: c.secure,
    sameSite: c.sameSite === 'no_restriction' ? 'None' : c.sameSite === 'lax' ? 'Lax' : c.sameSite === 'strict' ? 'Strict' : 'None',
  })).filter(c => c.name);

  console.log('Loading cookies, count:', cookies.length);
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1366, height: 900 },
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    locale: 'zh-CN',
  });
  console.log('Adding cookies...');
  await context.addCookies(cookies);

  const page = await context.newPage();
  try {
    console.log('Navigating...');
    await page.goto('https://x.com/elonmusk', { waitUntil: 'domcontentloaded', timeout: 30000 });
    console.log('Waiting for elements (12s)...');
    await page.waitForTimeout(12000);
    
    // 保存截图以便多模态排查
    await page.screenshot({ path: `${WS}/data/test_elon.png` });
    console.log('Screenshot saved.');

    // 检查页面是不是爆红或者由于 X 改版 selector 不能用
    const pageText = await page.innerText('body');
    console.log('--- Body text length:', pageText.length);
    console.log('--- Body sample (first 500 chars):');
    console.log(pageText.slice(0, 500));

    // 查看页面上 article 和 tweet testid 匹配数
    const articlesCount = await page.locator('article').count();
    const testidCount = await page.locator('article[data-testid="tweet"]').count();
    console.log(`Articles count: ${articlesCount}, Tweet-TestID count: ${testidCount}`);

  } catch (e) {
    console.error('Scrape exception:', e);
  } finally {
    await browser.close();
  }
})();
