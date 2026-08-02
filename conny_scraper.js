const { chromium } = require('playwright');
const fs = require('fs');

const BASE = 'F:/Users/Administrator/Documents/WorkBuddy/2026-07-24-21-36-14';
const DEBUG = BASE + '/conny_debug';
const USER = 'GuodongW18138';
const PASS = 'wgdfenix807822';
const TARGET = 'Conny_vv';

(async () => {
  fs.mkdirSync(DEBUG, { recursive: true });
  const log = (...a) => console.log('[LOG]', ...a);
  const shot = async (n) => { try { await page.screenshot({ path: `${DEBUG}/${n}.png` }); } catch (e) {} };

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1280, height: 900 },
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36'
  });
  const page = await context.newPage();

  // ---- 1. 登录 ----
  log('goto login');
  await page.goto('https://x.com/i/flow/login', { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(3500);
  await shot('1_login');

  await page.waitForSelector('input[type="text"]', { timeout: 15000 });
  await page.fill('input[type="text"]', USER);
  await page.waitForTimeout(900);
  await shot('2_user');

  const clickSubmit = () => page.evaluate(() => {
    const btns = Array.from(document.querySelectorAll('button[type="submit"]'));
    for (const b of btns) {
      const r = b.getBoundingClientRect();
      if (r.width > 0 && r.height > 0 && !b.disabled) { b.click(); return true; }
    }
    return false;
  });

  await clickSubmit();
  log('clicked continue (user)');
  await page.waitForTimeout(3500);
  await shot('3_after_user');

  // 检测限流
  const limited = await page.evaluate(() => /temporarily limited/i.test(document.body.innerText));
  if (limited) { log('RATE LIMITED on username step'); await browser.close(); return; }

  await page.waitForSelector('input[type="password"]', { timeout: 15000 });
  await page.fill('input[type="password"]', PASS);
  await page.waitForTimeout(900);
  await shot('4_pass');

  await clickSubmit();
  log('clicked continue (pass)');
  await page.waitForTimeout(10000);
  await shot('5_after_login');

  const cookies = await context.cookies();
  const hasAuth = cookies.some(c => c.name === 'auth_token');
  log('hasAuth', hasAuth);
  fs.writeFileSync(`${BASE}/conny_cookies.json`, JSON.stringify(cookies, null, 2));

  if (!hasAuth) {
    const stillLimited = await page.evaluate(() => /temporarily limited/i.test(document.body.innerText));
    log('LOGIN FAILED. rateLimited=', stillLimited, ' url=', page.url());
    await browser.close();
    return;
  }

  // ---- 2. 抓取目标推文 ----
  await page.goto(`https://x.com/${TARGET}`, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(5000);
  await shot('6_profile');

  const seen = new Set();
  const tweets = [];
  for (let i = 0; i < 18; i++) {
    const items = await page.evaluate(() => {
      const out = [];
      const arts = document.querySelectorAll('article[data-testid="tweet"]');
      for (const art of arts) {
        const tEl = art.querySelector('[data-testid="tweetText"]');
        const text = tEl ? tEl.innerText : '';
        let likes = 0, rts = 0;
        const likeEl = art.querySelector('[data-testid="like"]');
        if (likeEl) { const m = (likeEl.getAttribute('aria-label') || '').match(/([\d,]+)\s*Like/i); if (m) likes = parseInt(m[1].replace(/,/g, ''), 10); }
        const rtEl = art.querySelector('[data-testid="retweet"]');
        if (rtEl) { const m = (rtEl.getAttribute('aria-label') || '').match(/([\d,]+)\s*Retweet/i); if (m) rts = parseInt(m[1].replace(/,/g, ''), 10); }
        const isRetweet = /reposted|retweeted/i.test(art.innerText.slice(0, 120));
        const sensitive = /nsfw|adult|18\+/i.test(text);
        out.push({ text, likes, retweets: rts, is_retweet: isRetweet, is_sensitive: sensitive });
      }
      return out;
    });
    for (const it of items) {
      const key = (it.text || '').slice(0, 60);
      if (key && !seen.has(key)) { seen.add(key); tweets.push(it); }
    }
    log('scroll', i, 'collected', tweets.length);
    await page.evaluate(() => window.scrollBy(0, 1600));
    await page.waitForTimeout(2200);
  }
  await shot('7_tweets');

  // ---- 3. 合并资料 + 推文 ----
  let profile = {};
  try {
    const fx = JSON.parse(fs.readFileSync(`${BASE}/data/conny_vv_fxtwitter.json`, 'utf8'));
    const u = fx.user || {};
    profile = {
      name: u.name,
      description: u.description,
      followers_count: u.followers,
      following_count: u.following,
      tweets_count: u.tweets,
      location: u.location,
      joined: u.joined,
      is_sensitive: false,
      protected: !!u.protected
    };
  } catch (e) { log('profile read err', e.message); }

  const result = {
    username: TARGET,
    account_status: 'normal',
    is_sensitive: false,
    profile,
    recent_tweets: tweets
  };
  fs.writeFileSync(`${BASE}/conny_vv_data.json`, JSON.stringify(result, null, 2));
  log('DONE. tweets=', tweets.length, 'followers=', profile.followers_count);
  await browser.close();
})().catch(e => { console.error('FATAL', e); process.exit(1); });
