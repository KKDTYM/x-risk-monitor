const { chromium } = require('playwright');
const fs = require('fs');
const TARGET = process.argv[2] || 'zixuanmiao';
const WS = process.argv[3] || process.cwd();
const COOKIE_FILE = process.argv[4] || require('path').join(WS, 'conny_cookies.json');
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

  // 1) 自动补全
  await page.goto(`https://x.com/${TARGET}`, { waitUntil: 'domcontentloaded', timeout: 45000 });
  await page.waitForTimeout(6000);
  await page.click('a[href="/search"], a[aria-label*="搜索"], [data-testid="SearchBox_Search_Input"]').catch(() => {});
  await page.waitForTimeout(1200);
  const input = page.locator('input[data-testid="SearchBox_Search_Input"]');
  let auto = [];
  if (await input.count()) {
    await input.fill(TARGET);
    await page.waitForTimeout(2500);
    auto = await page.evaluate(() =>
      [...document.querySelectorAll('[data-testid="typeaheadResult"]')].slice(0, 8).map(i => (i.innerText || '').replace(/\n/g, ' ').slice(0, 90))
    );
  }
  console.log('AUTOCOMPLETE:', JSON.stringify(auto, null, 2));

  // 2) 用户搜索
  await page.goto(`https://x.com/search?q=${TARGET}&src=typed_query&f=user`, { waitUntil: 'domcontentloaded', timeout: 45000 });
  await page.waitForTimeout(9000);
  const u = await page.evaluate(() => {
    const cells = [...document.querySelectorAll('[data-testid="UserCell"]')];
    const handles = cells.map(c => {
      const a = [...c.querySelectorAll('a[href^="/"]')].find(x => /^\/([A-Za-z0-9_]{1,15})$/.test(x.getAttribute('href')));
      return a ? a.getAttribute('href').slice(1) : '';
    });
    const body = document.body?.innerText || '';
    return { count: cells.length, handles, noResult: /没有找到|no results/i.test(body) };
  });
  console.log('USER-SEARCH:', JSON.stringify(u, null, 2));

  // 3) from: 推文搜索
  await page.goto(`https://x.com/search?q=from%3A${TARGET}&src=typed_query&f=live`, { waitUntil: 'domcontentloaded', timeout: 45000 });
  await page.waitForTimeout(9000);
  const f = await page.evaluate(() => {
    const arts = [...document.querySelectorAll('article[data-testid="tweet"]')];
    const body = document.body?.innerText || '';
    return {
      articles: arts.length,
      noResult: /没有关于|no results/i.test(body),
      firstTexts: arts.slice(0, 4).map(a => (a.innerText || '').replace(/\n/g, ' ').slice(0, 80)),
    };
  });
  console.log('FROM-SEARCH:', JSON.stringify(f, null, 2));
  await browser.close();
})().catch(e => { console.error('FATAL', e); process.exit(1); });
