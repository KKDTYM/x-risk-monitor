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

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1366, height: 900 },
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    locale: 'zh-CN',
  });
  await context.addCookies(cookies);

  const page = await context.newPage();
  try {
    console.log('Navigating to @sunny31059...');
    await page.goto('https://x.com/sunny31059', { waitUntil: 'domcontentloaded', timeout: 30000 });
    await page.waitForTimeout(6000);
    
    // 截个图看看究竟
    await page.screenshot({ path: `${WS}/data/test_sunny.png` });
    console.log('Screenshot saved to data/test_sunny.png');

    // 检查页面是不是有敏感媒体阻断，或者需要特定的点击
    const html = await page.content();
    fs.writeFileSync(`${WS}/data/test_sunny.html`, html);
    console.log('HTML saved.');
  } catch (e) {
    console.error('Error:', e);
  } finally {
    await browser.close();
  }
})();
