const { chromium } = require('playwright');
const fs = require('fs');
const TARGET = process.argv[2] || 'zixuanmiao';
const WS = process.argv[3] || process.cwd();
const COOKIE_FILE = process.argv[4] || require('path').join(WS, 'conny_cookies.json');
const delay = ms => new Promise(r => setTimeout(r, ms));
(async () => {
  const raw = JSON.parse(fs.readFileSync(COOKIE_FILE, 'utf8'));
  const cookies = raw.map(c => ({
    name: c.name, value: c.value, domain: c.domain, path: c.path || '/',
    expires: c.expirationDate ? Math.floor(c.expirationDate) : undefined,
    httpOnly: c.httpOnly, secure: c.secure,
    sameSite: c.sameSite === 'no_restriction' ? 'None' : c.sameSite === 'lax' ? 'Lax' : c.sameSite === 'strict' ? 'Strict' : 'None',
  })).filter(c => c.name);
  const browser = await chromium.launch({ channel: 'msedge', headless: true, args: ['--disable-blink-features=AutomationControlled', '--no-sandbox'] });
  const context = await browser.newContext({
    viewport: { width: 1366, height: 900 },
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    locale: 'zh-CN',
  });
  await context.addCookies(cookies);
  const page = await context.newPage();
  await page.goto('https://x.com/home', { waitUntil: 'domcontentloaded', timeout: 45000 });
  await page.waitForTimeout(7000);
  const input = page.locator('input[data-testid="SearchBox_Search_Input"]');
  if (!(await input.count())) { console.log('input not found'); await browser.close(); return; }
  await input.click();
  await delay(800);
  await input.type(TARGET, { delay: 120 });
  await page.waitForTimeout(3500);
  const results = await page.evaluate(() =>
    [...document.querySelectorAll('[data-testid="typeaheadResult"]')].slice(0, 10).map(i => (i.innerText || '').replace(/\n/g, ' ').slice(0, 100))
  );
  console.log('AUTOCOMPLETE RETEST:', JSON.stringify(results, null, 2));
  await browser.close();
})().catch(e => { console.error('FATAL', e); process.exit(1); });
