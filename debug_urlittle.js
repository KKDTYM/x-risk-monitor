const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const WS = 'F:/Users/Administrator/Documents/WorkBuddy/2026-07-24-21-36-14';
const TARGET = 'urlittlecuteboy';

(async () => {
  const raw = JSON.parse(fs.readFileSync(`${WS}/conny_cookies.json`, 'utf8'));
  const cookies = raw.map(c => ({
    name: c.name, value: c.value, domain: c.domain, path: c.path || '/',
    expires: c.expirationDate ? Math.floor(c.expirationDate) : undefined,
    httpOnly: c.httpOnly, secure: c.secure,
    sameSite: c.sameSite === 'no_restriction' ? 'None' : c.sameSite === 'lax' ? 'Lax' : c.sameSite === 'strict' ? 'Strict' : 'None',
  })).filter(c => c.name);

  const browser = await chromium.launch({ headless: true, args: ['--disable-blink-features=AutomationControlled', '--no-sandbox'] });
  const context = await browser.newContext({
    viewport: { width: 1366, height: 900 },
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    locale: 'zh-CN',
  });
  await context.addCookies(cookies);
  const page = await context.newPage();

  console.log('[1] goto @urlittlecuteboy');
  await page.goto(`https://x.com/${TARGET}`, { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.waitForTimeout(5000);

  console.log('[2] scrolling 3 times...');
  for (let i = 0; i < 3; i++) {
    await page.evaluate(() => window.scrollBy(0, 1000));
    await page.waitForTimeout(2000);
  }

  console.log('[3] taking screenshot...');
  if (!fs.existsSync(`${WS}/data`)) {
    fs.mkdirSync(`${WS}/data`, { recursive: true });
  }
  await page.screenshot({ path: `${WS}/data/debug_urlittle.png` });

  console.log('[4] collecting elements and html...');
  const tweetCount = await page.locator('article[data-testid="tweet"]').count();
  const htmlContent = await page.content();
  const htmlPrefix = htmlContent.slice(0, 500);

  const txtContent = `Tweet Count: ${tweetCount}\nHTML Prefix:\n${htmlPrefix}`;
  fs.writeFileSync(`${WS}/data/debug_urlittle.txt`, txtContent, 'utf8');

  console.log(`Saved screenshot and text file. Tweet count found: ${tweetCount}`);

  await browser.close();
  console.log('=== DONE ===');
})().catch(e => {
  console.error('FATAL', e);
  process.exit(1);
});
