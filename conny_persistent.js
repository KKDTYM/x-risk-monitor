const { chromium } = require('playwright');
const fs = require('fs');

const WS = 'F:/Users/Administrator/Documents/WorkBuddy/2026-07-24-21-36-14';
const TARGET = 'Conny_vv';
const DEBUG = `${WS}/conny_debug_persist`;
const USERDATA = `${WS}/browser_profile`;   // persistent session stored here

if (!fs.existsSync(DEBUG)) fs.mkdirSync(DEBUG, { recursive: true });
const save = (name, buf) => fs.writeFileSync(`${DEBUG}/${name}.png`, buf);
const delay = (ms) => new Promise(r => setTimeout(r, ms));

(async () => {
  console.log('╔══════════════════════════════════════════╗');
  console.log('║  Persistent browser — session saved to    ║');
  console.log(`║  ${USERDATA.slice(0, 38)}...`);
  console.log('╚══════════════════════════════════════════╝\n');

  const context = await chromium.launchPersistentContext(USERDATA, {
    headless: false,
    args: ['--disable-blink-features=AutomationControlled', '--no-sandbox', '--start-maximized'],
    viewport: { width: 1920, height: 1080 },
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    locale: 'zh-CN',
  });

  await context.addInitScript(() => {
    Object.defineProperty(navigator, 'webdriver', { get: () => false });
    try { Object.defineProperty(navigator, 'plugins', { get: () => [1,2,3,4,5] }); } catch(e){}
    try { Object.defineProperty(navigator, 'languages', { get: () => ['zh-CN','zh','en'] }); } catch(e){}
  });

  const page = await context.newPage();

  // Check if already logged in from a previous run
  const existingCookies = await context.cookies();
  const alreadyAuth = existingCookies.some(c => /auth_token|ct0/.test(c.name));
  console.log(alreadyAuth ? '[✓] Found saved session — skipping login.' : '[!] No saved session — please login.');

  if (!alreadyAuth) {
    console.log('[→] Opening X login page. Please login as @GuodongW18138.\n');
    await page.goto('https://x.com/login', { waitUntil: 'networkidle', timeout: 45000 }).catch(()=>{});
    await delay(3000);
    await save('01_login_ready', await page.screenshot());

    let loggedIn = false;
    for (let i = 1; i <= 160; i++) {
      await delay(3000);
      const cookies = await context.cookies();
      const isAuth = cookies.some(c => /auth_token|ct0/.test(c.name));
      const url = page.url();
      // Detect login by EITHER auth cookies OR URL jumping to home/profile
      if (isAuth || /^https:\/\/x\.com\/(home|\/)?$/.test(url) || /x\.com\/[A-Za-z0-9_]+\/?$/.test(url)) {
        if (isAuth) {
          loggedIn = true;
          console.log(`\n[✓✓✓] LOGIN DETECTED (cookies) at ${i*3}s!`);
          break;
        }
        // URL changed to home but no cookie yet — wait a bit for cookie to settle
        if (i > 5) {
          console.log(`\n[~] Home URL detected at ${i*3}s, waiting for cookies to settle...`);
          await delay(3000);
          const c2 = await context.cookies();
          if (c2.some(c => /auth_token|ct0/.test(c.name))) {
            loggedIn = true;
            console.log('[✓✓✓] Cookies settled!');
            break;
          }
        }
      }
      if (i % 10 === 0) {
        try { console.log(`   [${i*3}s] waiting... url=${url.slice(0,55)}`); }
        catch(e) { console.log(`   [${i*3}s] (browser closed)`); }
      }
    }
    if (!loggedIn) {
      console.log('\n[!] Timeout — please keep the window OPEN until I start scraping.');
      try { await save('99_timeout', await page.screenshot()); } catch(e){}
      try { await context.close(); } catch(e){}
      process.exit(2);
    }
    // Save cookies snapshot
    const cookies = await context.cookies();
    fs.writeFileSync(`${WS}/conny_auth_cookies.json`, JSON.stringify(cookies, null, 2));
  }

  // ===== SCRAPE @Conny_vv =====
  console.log(`\n[1] Navigating to https://x.com/${TARGET} ...`);
  await page.goto(`https://x.com/${TARGET}`, { waitUntil: 'domcontentloaded', timeout: 30000 });
  await delay(6000);
  await save('03_profile', await page.screenshot());

  console.log('[2] Scrolling to load tweets...');
  let lastN = 0, stale = 0;
  for (let i = 0; i < 30; i++) {
    await page.evaluate(() => window.scrollBy(0, 1200));
    await delay(1800);
    const n = await page.evaluate(() => document.querySelectorAll('article[data-testid="tweet"]').length);
    if (n === lastN) stale++; else stale = 0;
    if ((i+1) % 5 === 0 || n !== lastN) console.log(`   scroll ${(i+1)}: ${n} tweets`);
    if (stale >= 4 && n > 0) break;
    lastN = n;
  }
  await save('04_tweets', await page.screenshot());

  const tweets = await page.evaluate(() => {
    return Array.from(document.querySelectorAll('article[data-testid="tweet"]')).map(art => ({
      text: (art.querySelector('div[lang]')?.innerText || '').slice(0, 1000),
      time: art.querySelector('time')?.getAttribute('datetime') || '',
      replies: (() => { const el = art.querySelector('[aria-label*="repl"], [aria-label*="回复"]'); return el?.getAttribute('aria-label')||''; })(),
      retweets: (() => { const el = art.querySelector('[aria-label*="Retweet"], [aria-label*="转"]'); return el?.getAttribute('aria-label')||''; })(),
      likes: (() => { const el = art.querySelector('[aria-label*="Like"], [aria-label*="喜欢"]'); return el?.getAttribute('aria-label')||''; })(),
      views: (() => { const el = art.querySelector('[aria-label*="view"], [aria-label*="浏览"]'); return el?.getAttribute('aria-label')||''; })(),
      hasMedia: !!art.querySelector('img[data-testid="tweetPhoto"], video'),
    })).filter(t => t.text.trim());
  });

  console.log(`\n[✓] Got ${tweets.length} tweets!\n`);
  fs.writeFileSync(`${WS}/data/conny_vv_tweets.json`, JSON.stringify(tweets, null, 2));

  tweets.forEach((t, i) => {
    console.log(`--- Tweet ${i+1}/${tweets.length} (${t.time}) ---`);
    console.log(`${t.text.slice(0, 200).replace(/\n/g,' ')} | ❤️${t.likes} 🔁${t.retweets}`);
  });

  const profile = await page.evaluate(() => ({
    name: document.querySelector('div[data-testid="UserName"]')?.innerText?.slice(0, 100) || '',
    bio: (document.querySelector('div[data-testid="UserDescription"]')?.innerText || '').slice(0, 200),
    stats: [...document.querySelectorAll('a[href]')].filter(a => /^\d+\s/.test(a.innerText)).map(a=>a.innerText).join(' | '),
  }));
  fs.writeFileSync(`${WS}/data/conny_vv_profile.json`, JSON.stringify(profile, null, 2));
  console.log('\n--- Profile ---\n' + JSON.stringify(profile, null, 2));

  await delay(500);
  await context.close();
  console.log('\n=== DONE ✓ (session saved for next time) ===');
})().catch(e => {
  console.error('FATAL:', e.message);
  try { process.exit(1); } catch {}
});
