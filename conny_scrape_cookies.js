const { chromium } = require('playwright');
const fs = require('fs');

const WS = 'F:/Users/Administrator/Documents/WorkBuddy/2026-07-24-21-36-14';
const TARGET = 'Conny_vv';
const DEBUG = `${WS}/conny_debug_cookies`;

if (!fs.existsSync(DEBUG)) fs.mkdirSync(DEBUG, { recursive: true });
const save = (n, b) => fs.writeFileSync(`${DEBUG}/${n}.png`, b);
const delay = ms => new Promise(r => setTimeout(r, ms));

(async () => {
  // Load + convert Cookie-Editor export -> Playwright format
  const raw = JSON.parse(fs.readFileSync(`${WS}/conny_cookies.json`, 'utf8'));
  const cookies = raw.map(c => ({
    name: c.name,
    value: c.value,
    domain: c.domain,
    path: c.path || '/',
    expires: c.expirationDate ? Math.floor(c.expirationDate) : undefined,
    httpOnly: c.httpOnly,
    secure: c.secure,
    sameSite: c.sameSite === 'no_restriction' ? 'None'
            : c.sameSite === 'lax' ? 'Lax'
            : c.sameSite === 'strict' ? 'Strict' : 'None',
  })).filter(c => c.name); // drop any malformed
  console.log(`[✓] Loaded ${cookies.length} cookies`);
  console.log('   auth_token:', cookies.some(c => c.name === 'auth_token'));
  console.log('   ct0:', cookies.some(c => c.name === 'ct0'));

  const browser = await chromium.launch({
    headless: true,
    args: ['--disable-blink-features=AutomationControlled', '--no-sandbox'],
  });
  const context = await browser.newContext({
    viewport: { width: 1366, height: 900 },
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    locale: 'zh-CN',
  });
  await context.addCookies(cookies);
  const page = await context.newPage();

  console.log('\n[1] Navigating to @Conny_vv with cookies...');
  await page.goto(`https://x.com/${TARGET}`, { waitUntil: 'domcontentloaded', timeout: 30000 });
  await delay(6000);
  await save('01_profile', await page.screenshot());

  // Verify login success
  const state = await page.evaluate(() => {
    const body = document.body?.innerText || '';
    const tweets = document.querySelectorAll('article[data-testid="tweet"]').length;
    const loginPrompt = /登录|Log in|Sign in|注册/.test(body.slice(0, 800));
    return { tweets, loginPrompt, url: location.href };
  });
  console.log('   url:', state.url);
  console.log('   tweets visible:', state.tweets, '| loginPrompt:', state.loginPrompt);
  if (state.loginPrompt && state.tweets === 0) {
    console.log('[!] Cookies rejected — showing login prompt');
    await save('01_rejected', await page.screenshot());
    await browser.close();
    process.exit(3);
  }

  // Scroll to load all tweets
  console.log('\n[2] Scrolling to load tweets...');
  let lastN = 0, stale = 0;
  for (let i = 0; i < 35; i++) {
    await page.evaluate(() => window.scrollBy(0, 1200));
    await delay(1700);
    const n = await page.evaluate(() => document.querySelectorAll('article[data-testid="tweet"]').length);
    if (n === lastN) stale++; else stale = 0;
    if ((i + 1) % 5 === 0 || n !== lastN) console.log(`   scroll ${i + 1}: ${n} tweets`);
    if (stale >= 4 && n > 0) { console.log('   (stable, stopping)'); break; }
    lastN = n;
  }
  await save('02_tweets', await page.screenshot());

  // Extract tweets
  const tweets = await page.evaluate(() => {
    return Array.from(document.querySelectorAll('article[data-testid="tweet"]')).map(art => ({
      text: (art.querySelector('div[lang]')?.innerText || '').slice(0, 1200),
      time: art.querySelector('time')?.getAttribute('datetime') || '',
      replies: art.querySelector('[aria-label*="repl"], [aria-label*="回复"]')?.getAttribute('aria-label') || '',
      retweets: art.querySelector('[aria-label*="Retweet"], [aria-label*="转"]')?.getAttribute('aria-label') || '',
      likes: art.querySelector('[aria-label*="Like"], [aria-label*="喜欢"]')?.getAttribute('aria-label') || '',
      views: art.querySelector('[aria-label*="view"], [aria-label*="浏览"]')?.getAttribute('aria-label') || '',
      hasMedia: !!art.querySelector('img[data-testid="tweetPhoto"], video'),
    })).filter(t => t.text.trim());
  });

  console.log(`\n[✓] Extracted ${tweets.length} tweets from @${TARGET}`);
  fs.writeFileSync(`${WS}/data/conny_vv_tweets.json`, JSON.stringify(tweets, null, 2));

  console.log('\n--- PREVIEW (first 12) ---');
  tweets.slice(0, 12).forEach((t, i) => {
    console.log(`\n[${i + 1}] ${t.time || 'no-date'} | ❤️${t.likes} 🔁${t.retweets} | media:${t.hasMedia}`);
    console.log(t.text.slice(0, 220).replace(/\n/g, ' '));
  });

  // Profile info
  const profile = await page.evaluate(() => ({
    name: document.querySelector('div[data-testid="UserName"]')?.innerText?.replace(/\n/g, ' ')?.slice(0, 80) || '',
    bio: (document.querySelector('div[data-testid="UserDescription"]')?.innerText || '').slice(0, 300),
    stats: [...document.querySelectorAll('a[href]')]
      .map(a => a.innerText?.trim())
      .filter(t => /^(Following|Followers|\d+)/.test(t || ''))
      .slice(0, 4),
  }));
  fs.writeFileSync(`${WS}/data/conny_vv_profile.json`, JSON.stringify(profile, null, 2));
  console.log('\n--- PROFILE ---');
  console.log(JSON.stringify(profile, null, 2));

  await browser.close();
  console.log('\n=== DONE ✓ ===');
})().catch(e => { console.error('FATAL', e); process.exit(1); });
