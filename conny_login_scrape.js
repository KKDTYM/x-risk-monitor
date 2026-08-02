const { chromium } = require('playwright');
const fs = require('fs');

const WS = 'F:/Users/Administrator/Documents/WorkBuddy/2026-07-24-21-36-14';
const USER = 'GuodongW18138';
const PASS = 'wgdfenix807822';
const TARGET = 'Conny_vv';
const DEBUG = `${WS}/conny_debug2`;

if (!fs.existsSync(DEBUG)) fs.mkdirSync(DEBUG, { recursive: true });
const save = (name, buf) => fs.writeFileSync(`${DEBUG}/${name}.png`, buf);
const delay = (ms) => new Promise(r => setTimeout(r, ms));

(async () => {
  const browser = await chromium.launch({
    headless: true,
    args: [
      '--disable-blink-features=AutomationControlled',
      '--no-sandbox',
      '--disable-dev-shm-usage',
    ],
  });
  const context = await browser.newContext({
    viewport: { width: 1366, height: 900 },
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    locale: 'zh-CN',
  });
  // stealth: kill navigator.webdriver + patch plugins/languages
  await context.addInitScript(() => {
    Object.defineProperty(navigator, 'webdriver', { get: () => false });
    try {
      Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
      Object.defineProperty(navigator, 'languages', { get: () => ['zh-CN', 'zh', 'en'] });
    } catch (e) {}
    const orig = window.HTMLElement.prototype.click;
    // no-op patch just to make property look native
  });

  const page = await context.newPage();
  page.on('console', m => { if (m.type() === 'error') console.log('  [console.err]', m.text().slice(0, 120)); });

  console.log('[1] goto login');
  await page.goto('https://x.com/i/flow/login', { waitUntil: 'domcontentloaded', timeout: 30000 });
  await delay(3000);
  await save('1_login', await page.screenshot());

  // username
  console.log('[2] fill username');
  const userSel = 'input[name="text"], input[autocomplete="username"], input[type="text"]';
  await page.waitForSelector(userSel, { timeout: 15000 });
  await page.fill(userSel, USER);
  await delay(1200);
  await save('2_user', await page.screenshot());

  // click Continue (could be 继续 / Next / Log in)
  console.log('[3] click Continue');
  const clicked = await page.evaluate(() => {
    const btns = Array.from(document.querySelectorAll('button[type="submit"], div[role="button"]'));
    const b = btns.find(x => /继续|Next|Log ?in|登录|下一步/i.test(x.innerText || ''));
    if (b) { b.click(); return (b.innerText || '').trim(); }
    const any = document.querySelector('button[type="submit"]');
    if (any) { any.click(); return 'submit-fallback'; }
    return 'none';
  });
  console.log('   clicked:', clicked);
  await delay(4000);
  await save('3_after_user', await page.screenshot());

  // check for rate limit
  const limited = await page.evaluate(() => /temporarily limited|暂时限制/i.test(document.body.innerText || ''));
  if (limited) {
    console.log('[!] RATE LIMITED again');
    await save('3_limited', await page.screenshot());
    await browser.close();
    process.exit(2);
  }

  // password
  console.log('[4] fill password');
  const passSel = 'input[name="password"], input[type="password"]';
  await page.waitForSelector(passSel, { timeout: 15000 });
  await page.fill(passSel, PASS);
  await delay(1200);
  await save('4_pass', await page.screenshot());

  // click Log in / 登录 / 继续
  console.log('[5] submit login');
  const clicked2 = await page.evaluate(() => {
    const btns = Array.from(document.querySelectorAll('button[type="submit"], div[role="button"]'));
    const b = btns.find(x => /继续|Log ?in|登录|Sign ?in/i.test(x.innerText || ''));
    if (b) { b.click(); return (b.innerText || '').trim(); }
    const any = document.querySelector('button[type="submit"]');
    if (any) { any.click(); return 'submit-fallback'; }
    return 'none';
  });
  console.log('   clicked:', clicked2);

  // wait for home or onboarding
  await delay(8000);
  await save('5_after_login', await page.screenshot());

  // check cookies for auth_token
  const cookies = await context.cookies();
  const hasAuth = cookies.some(c => /auth_token|ct0/.test(c.name));
  console.log('[6] auth cookies present:', hasAuth, '| total', cookies.length);
  if (hasAuth) {
    fs.writeFileSync(`${WS}/conny_auth_cookies.json`, JSON.stringify(cookies, null, 2));
  }

  if (!hasAuth) {
    console.log('[!] No auth cookies — login not completed');
    await browser.close();
    process.exit(3);
  }

  console.log('[7] nav to @Conny_vv and scrape tweets');
  await page.goto(`https://x.com/${TARGET}`, { waitUntil: 'domcontentloaded', timeout: 30000 });
  await delay(5000);
  await save('6_target_profile', await page.screenshot());

  // scroll to load tweets
  let lastCount = 0;
  for (let i = 0; i < 12; i++) {
    await page.evaluate(() => window.scrollBy(0, 1200));
    await delay(1500);
    const n = await page.evaluate(() => document.querySelectorAll('article[data-testid="tweet"]').length);
    if (n === lastCount && i > 3) break;
    lastCount = n;
  }
  await save('7_target_tweets', await page.screenshot());

  // extract tweets
  const tweets = await page.evaluate(() => {
    const out = [];
    const arts = document.querySelectorAll('article[data-testid="tweet"]');
    arts.forEach(art => {
      const txt = art.querySelector('div[lang]')?.innerText || '';
      const time = art.querySelector('time')?.getAttribute('datetime') || '';
      const statSpans = art.querySelectorAll('span');
      let replies = '', retweets = '', likes = '';
      // find group with aria-label stats
      const groups = art.querySelectorAll('div[role="group"]');
      groups.forEach(g => {
        g.querySelectorAll('[aria-label]').forEach(el => {
          const lbl = el.getAttribute('aria-label') || '';
          if (/repl|回复/i.test(lbl)) replies = lbl;
          else if (/retr|转/i.test(lbl)) retweets = lbl;
          else if (/like|喜欢/i.test(lbl)) likes = lbl;
        });
      });
      if (txt) out.push({ text: txt.slice(0, 600), time, replies, retweets, likes });
    });
    return out;
  });

  console.log('[8] extracted tweets:', tweets.length);
  fs.writeFileSync(`${WS}/data/conny_vv_tweets.json`, JSON.stringify(tweets, null, 2));
  console.log(JSON.stringify(tweets.slice(0, 3), null, 2));

  await browser.close();
  console.log('DONE');
})().catch(e => { console.error('FATAL', e); process.exit(1); });
