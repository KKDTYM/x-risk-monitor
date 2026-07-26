const { chromium } = require('playwright');
const fs = require('fs');

const WS = 'F:/Users/Administrator/Documents/WorkBuddy/2026-07-24-21-36-14';
const USER = 'GuodongW18138';
const PASS = 'wgdfenix807822';
const TARGET = 'Conny_vv';
const DEBUG = `${WS}/conny_debug3`;

if (!fs.existsSync(DEBUG)) fs.mkdirSync(DEBUG, { recursive: true });
const save = (name, buf) => fs.writeFileSync(`${DEBUG}/${name}.png`, buf);
const delay = (ms) => new Promise(r => setTimeout(r, ms));

// Helper: find and click the PRIMARY action button, EXCLUDING OAuth buttons
async function clickPrimaryButton(page) {
  const result = await page.evaluate(() => {
    // Collect all clickable elements
    const candidates = Array.from(document.querySelectorAll('button[type="submit"], div[role="button"], button'));
    // Filter OUT OAuth / phone buttons
    const filtered = candidates.filter(el => {
      const text = (el.innerText || el.textContent || '').trim();
      return !/google|facebook|apple|phone|手机/i.test(text) && text.length > 0;
    });
    // Prefer the one that looks like a primary submit (short text like 继续/Next/Log in)
    const primary = filtered.find(el => {
      const t = (el.innerText || '').trim();
      return /^(继续|Next|Log ?in|登录|Sign ?in|Submit)$/i.test(t);
    }) || filtered.find(el => {
      const t = (el.innerText || '').trim();
      return t.length < 20; // short button text
    }) || filtered[0];
    if (primary) {
      primary.click();
      return { ok: true, label: (primary.innerText || '').trim(), tag: primary.tagName };
    }
    return { ok: false, label: null };
  });
  console.log('   btn-click:', JSON.stringify(result));
  return result;
}

(async () => {
  const browser = await chromium.launch({
    headless: true,
    args: ['--disable-blink-features=AutomationControlled', '--no-sandbox'],
  });
  const context = await browser.newContext({
    viewport: { width: 1366, height: 900 },
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    locale: 'zh-CN',
  });

  // stealth patches
  await context.addInitScript(() => {
    Object.defineProperty(navigator, 'webdriver', { get: () => false });
    try {
      Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
      Object.defineProperty(navigator, 'languages', { get: () => ['zh-CN', 'zh', 'en'] });
    } catch(e) {}
  });

  const page = await context.newPage();

  console.log('[1] goto login');
  await page.goto('https://x.com/i/flow/login', { waitUntil: 'domcontentloaded', timeout: 30000 });
  await delay(4000);
  await save('01_login_page', await page.screenshot());

  // Step 2: Fill username in the VISIBLE input inside the dialog
  console.log('[2] fill username');
  // Use multiple strategies to find the username input
  let filled = false;
  for (const sel of [
    'input[name="text"]',
    'input[autocomplete="username"]',
    'input[type="text"]',
    '#layers input[type="text"]',
    '[data-testid="ocfEnterTextTextInput"]',
  ]) {
    try {
      const el = await page.$(sel);
      if (el && await el.isVisible()) {
        await el.click({ delay: 100 });
        await el.type(USER, { delay: 80 }); // type character by character
        filled = true;
        console.log('   filled via:', sel);
        break;
      }
    } catch(e) {}
  }
  if (!filled) {
    // fallback: use evaluate to find visible input
    await page.evaluate((u) => {
      const inputs = document.querySelectorAll('input');
      for (const inp of inputs) {
        if (inp.offsetParent !== null && (inp.type === 'text' || inp.name === 'text' || inp.autocomplete === 'username')) {
          inp.focus();
          inp.value = u;
          inp.dispatchEvent(new Event('input', { bubbles: true }));
          inp.dispatchEvent(new Event('change', { bubbles: true }));
          break;
        }
      }
    }, USER);
    console.log('   filled via evaluate');
  }
  await delay(1500);
  await save('02_username_filled', await page.screenshot());

  // Verify what's actually in the input
  const inputValue = await page.evaluate(() => {
    const inputs = document.querySelectorAll('input[type="text"], input[name="text"]');
    return Array.from(inputs).map(i => ({ val: i.value, vis: i.offsetParent !== null }));
  });
  console.log('   input values:', JSON.stringify(inputValue));

  // Step 3: Click Continue (NOT Google!)
  console.log('[3] click Continue');
  await clickPrimaryButton(page);
  await delay(5000);
  await save('03_after_continue', await page.screenshot());

  // Check rate limit
  const limited = await page.evaluate(() => /temporarily limited|暂时限制/i.test(document.body.innerText || ''));
  if (limited) {
    console.log('[!] RATE LIMITED!');
    await save('03_limited', await page.screenshot());
    await browser.close();
    process.exit(2);
  }

  // Check current URL
  console.log('   url:', page.url());

  // Step 4: Password
  console.log('[4] fill password');
  const passSel = 'input[name="password"], input[type="password"]';
  try {
    await page.waitForSelector(passSel, { timeout: 10000 });
    const passEl = await page.$(passSel);
    if (passEl) {
      await passEl.click({ delay: 100 });
      await passEl.type(PASS, { delay: 60 });
      console.log('   password typed');
    }
  } catch(e) {
    console.log('   password field not found, trying evaluate...');
    await page.evaluate((p) => {
      const inp = document.querySelector('input[type="password"], input[name="password"]');
      if (inp) { inp.focus(); inp.value = p; inp.dispatchEvent(new Event('input', {bubbles:true})); }
    }, PASS);
  }
  await delay(1500);
  await save('04_password_filled', await page.screenshot());

  // Step 5: Submit login
  console.log('[5] submit login');
  await clickPrimaryButton(page);

  // Wait for navigation or onboarding
  await delay(10000);
  await save('05_after_login', await page.screenshot());
  console.log('   url:', page.url());

  // Check cookies
  const cookies = await context.cookies();
  const hasAuth = cookies.some(c => /auth_token|ct0/.test(c.name));
  console.log('[6] auth cookies:', hasAuth, '| total:', cookies.length);
  if (hasAuth) {
    fs.writeFileSync(`${WS}/conny_auth_cookies.json`, JSON.stringify(cookies, null, 2));
    console.log('   auth cookie names:', cookies.filter(c => /auth_token|ct0/.test(c.name)).map(c => c.name + '=' + c.value.slice(0, 15) + '...'));
  }

  if (!hasAuth) {
    // Maybe we need to handle an extra step (email verification, etc.)
    console.log('[!] No auth yet — checking page state...');
    const bodyText = await page.evaluate(() => document.body?.innerText?.slice(0, 300) || '');
    console.log('   body preview:', bodyText.replace(/\n/g, ' | '));
    await browser.close();
    process.exit(3);
  }

  // ===== SCRAPE @Conny_vv =====
  console.log('[7] navigate to @Conny_vv');
  await page.goto(`https://x.com/${TARGET}`, { waitUntil: 'domcontentloaded', timeout: 30000 });
  await delay(6000);
  await save('06_conny_profile', await page.screenshot());

  // Scroll to load tweets
  let lastCount = 0;
  for (let i = 0; i < 15; i++) {
    await page.evaluate(() => window.scrollBy(0, 1200));
    await delay(1800);
    const n = await page.evaluate(() => document.querySelectorAll('article[data-testid="tweet"]').length);
    console.log(`   scroll ${i}: ${n} tweets`);
    if (n === lastCount && i > 4) break;
    lastCount = n;
  }
  await save('07_conny_tweets', await page.screenshot());

  // Extract tweet data
  const tweets = await page.evaluate(() => {
    const out = [];
    document.querySelectorAll('article[data-testid="tweet"]').forEach(art => {
      const txt = art.querySelector('div[lang]')?.innerText || '';
      const time = art.querySelector('time')?.getAttribute('datetime') || '';
      let replies = '', retweets = '', likes = '';
      art.querySelectorAll('[aria-label]').forEach(el => {
        const lbl = el.getAttribute('aria-label') || '';
        if (/repl|回复/i.test(lbl)) replies = lbl;
        else if (/retr|转|Retweet/i.test(lbl)) retweets = lbl;
        else if (/like|喜欢|Like/i.test(lbl)) likes = lbl;
      });
      if (txt.trim()) out.push({ text: txt.slice(0, 800), time, replies, retweets, likes });
    });
    return out;
  });

  console.log(`\n[8] === EXTRACTED ${tweets.length} TWEETS ===`);
  fs.writeFileSync(`${WS}/data/conny_vv_tweets.json`, JSON.stringify(tweets, null, 2));
  tweets.slice(0, 5).forEach((t, i) => console.log(`\n--- Tweet ${i+1} (${t.time}) ---\n${t.text.slice(0, 200)}\n`));

  await browser.close();
  console.log('\nDONE — tweets saved to data/conny_vv_tweets.json');
})().catch(e => { console.error('FATAL', e); process.exit(1); });
