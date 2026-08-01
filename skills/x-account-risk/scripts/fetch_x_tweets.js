const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

// Usage: node fetch_x_tweets.js <Handle> [workspace_dir] [cookie_file]
const TARGET = process.argv[2];
if (!TARGET) {
  console.error('Usage: node fetch_x_tweets.js <Handle> [workspace_dir] [cookie_file]');
  process.exit(2);
}
const WS = process.argv[3] || process.cwd();
const COOKIE_FILE = process.argv[4] || path.join(WS, 'conny_cookies.json');
const DEBUG = path.join(WS, 'zixuanmiao_debug');
if (!fs.existsSync(DEBUG)) fs.mkdirSync(DEBUG, { recursive: true });
const save = (n, b) => fs.writeFileSync(path.join(DEBUG, `${n}.png`), b);
const delay = ms => new Promise(r => setTimeout(r, ms));

(async () => {
  const raw = JSON.parse(fs.readFileSync(COOKIE_FILE, 'utf8'));
  const cookies = raw.map(c => ({
    name: c.name, value: c.value, domain: c.domain,
    path: c.path || '/',
    expires: c.expirationDate ? Math.floor(c.expirationDate) : undefined,
    httpOnly: c.httpOnly, secure: c.secure,
    sameSite: c.sameSite === 'no_restriction' ? 'None'
            : c.sameSite === 'lax' ? 'Lax'
            : c.sameSite === 'strict' ? 'Strict' : 'None',
  })).filter(c => c.name);
  console.log(`[✓] Loaded ${cookies.length} cookies from ${path.basename(COOKIE_FILE)}`);
  console.log('   auth_token:', cookies.some(c => c.name === 'auth_token'), '| ct0:', cookies.some(c => c.name === 'ct0'));

  const browser = await chromium.launch({
    headless: true,
    channel: 'msedge',
    args: ['--disable-blink-features=AutomationControlled', '--no-sandbox'],
  });
  const context = await browser.newContext({
    viewport: { width: 1366, height: 900 },
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    locale: 'zh-CN',
  });
  await context.addCookies(cookies);
  const page = await context.newPage();

  console.log(`\n[1] Navigating to @${TARGET}...`);
  await page.goto(`https://x.com/${TARGET}`, { waitUntil: 'domcontentloaded', timeout: 30000 });
  await delay(6000);

  // 自动等待并点击「此个人资料可能包含潜在的敏感内容」警告门上的“是，查看个人资料”按钮
  let clickedSensitiveGate = false;
  try {
    await page.locator('button[data-testid="empty_state_button_text"]').click({ timeout: 25000 });
    clickedSensitiveGate = true;
  } catch (e) {
    clickedSensitiveGate = await page.evaluate(() => {
      const btn = [...document.querySelectorAll('button, div[role="button"], a')]
        .find(b => /是，查看个人资料|查看个人资料|Yes, view profile|View profile/i.test(b.innerText || ''));
      if (btn) { try { btn.click(); return true; } catch (e2) { return false; } }
      return false;
    });
  }
  console.log('   sensitive-gate clicked:', clickedSensitiveGate);
  if (clickedSensitiveGate) await delay(5000);
  await save('01_profile', await page.screenshot());

  const state = await page.evaluate(() => {
    const body = document.body?.innerText || '';
    const tweets = document.querySelectorAll('article[data-testid="tweet"]').length;
    const loginPrompt = /登录|Log in|Sign in|注册/.test(body.slice(0, 800));
    return { tweets, loginPrompt, url: location.href };
  });
  console.log('   url:', state.url, '| tweets visible:', state.tweets, '| loginPrompt:', state.loginPrompt);
  if (state.loginPrompt && state.tweets === 0) {
    console.log('[!] Cookies rejected — login prompt shown. Export fresh cookies.');
    await save('rejected', await page.screenshot());
    await browser.close();
    process.exit(3);
  }

  console.log('\n[2] Scrolling + incremental collection...');
  const collected = new Map();
  const keyOf = t => (t.time || '') + '|' + t.text.slice(0, 50);
  const extract = () => {
    return Array.from(document.querySelectorAll('article[data-testid="tweet"]')).map(art => {
      const textEl = art.querySelector('div[lang]');
      const text = (textEl?.innerText || '').slice(0, 1500);
      // 自动展开被折叠的敏感媒体，否则 img 不在 DOM
      const blurBtn = [...art.querySelectorAll('button, div[role="button"]')]
        .find(b => /显示|查看|可能包含敏感/i.test(b.innerText || ''));
      if (blurBtn) { try { blurBtn.click(); } catch (e) {} }
      // 真实推文链接/ID
      const link = art.querySelector('a[href*="/status/"]');
      const permalink = link ? link.getAttribute('href') : '';
      const mId = permalink ? permalink.match(/\/status\/(\d+)/) : null;
      // 互动数字：从全部 aria-label 中按关键字提取
      const allLabels = [...art.querySelectorAll('[aria-label]')].map(e => e.getAttribute('aria-label')).join(' | ');
      const num = (re) => { const m = allLabels.match(re); return m ? m[1] : ''; };
      const likes = num(/([\d,]+)\s*喜欢/);
      const retweets = num(/([\d,]+)\s*次转帖/);
      const replies = num(/([\d,]+)\s*回复/);
      const views = num(/([\d,]+)\s*次观看/);
      const bookmarks = num(/([\d,]+)\s*书签/);
      // 媒体检测：img/video/图片容器
      const mediaEls = art.querySelectorAll('img[src*="pbs.twimg.com"], video, div[data-testid="tweetPhoto"], div[data-testid="tweetVideo"]');
      const hasMedia = mediaEls.length > 0;
      return {
        text,
        time: art.querySelector('time')?.getAttribute('datetime') || '',
        likes, retweets, replies, views, bookmarks,
        hasMedia,
        possibly_sensitive: /显示|可能包含敏感|sensitive|敏感内容/i.test(art.innerText),
        url: permalink ? 'https://x.com' + permalink.split('?')[0] : '',
        id: mId ? mId[1] : '',
      };
    }).filter(t => t.text.trim());
  };
  let lastN = 0, stale = 0;
  for (let i = 0; i < 40; i++) {
    await page.evaluate(() => window.scrollBy(0, 1500));
    await delay(1900);
    const batch = await page.evaluate(extract);
    for (const t of batch) { const k = keyOf(t); if (!collected.has(k)) collected.set(k, t); }
    const n = collected.size;
    if ((i + 1) % 3 === 0 || n !== lastN) console.log(`   scroll ${i + 1}: collected ${n}`);
    if (n === lastN) stale++; else stale = 0;
    if (stale >= 5 && n > 0) { console.log('   (stable, stopping)'); break; }
    lastN = n;
  }
  await save('02_tweets', await page.screenshot());
  const tweets = [...collected.values()];
  const lower = TARGET.toLowerCase();

  if (tweets.length === 0) {
    const diag = await page.evaluate(() => {
      const body = document.body?.innerText || '';
      return {
        url: location.href,
        bodyHead: body.slice(0, 900),
        articles: document.querySelectorAll('article[data-testid="tweet"]').length,
        gate: !!document.querySelector('button[data-testid="empty_state_button_text"]'),
      };
    });
    console.log('--- DIAG (0 tweets) ---');
    console.log(JSON.stringify(diag, null, 2));
  }

  console.log(`\n[✓] Extracted ${tweets.length} tweets from @${TARGET}`);
  fs.writeFileSync(path.join(WS, 'data', `${lower}_tweets.json`), JSON.stringify(tweets, null, 2));

  const profile = await page.evaluate(() => ({
    name: document.querySelector('div[data-testid="UserName"]')?.innerText?.replace(/\n/g, ' ')?.slice(0, 80) || '',
    bio: (document.querySelector('div[data-testid="UserDescription"]')?.innerText || '').slice(0, 300),
    stats: [...document.querySelectorAll('a[href]')]
      .map(a => a.innerText?.trim())
      .filter(t => /^(Following|Followers|\d+)/.test(t || ''))
      .slice(0, 4),
  }));
  fs.writeFileSync(path.join(WS, 'data', `${lower}_profile.json`), JSON.stringify(profile, null, 2));
  console.log('\n--- PROFILE ---');
  console.log(JSON.stringify(profile, null, 2));

  console.log('\n--- PREVIEW (first 8) ---');
  tweets.slice(0, 8).forEach((t, i) => {
    console.log(`\n[${i + 1}] ${t.time || 'no-date'} | ❤${t.likes} 🔁${t.retweets} | media:${t.hasMedia} | sens:${t.possibly_sensitive}`);
    console.log(t.text.slice(0, 160).replace(/\n/g, ' '));
  });

  await browser.close();
  console.log('\n=== DONE ✓ ===');
})().catch(e => { console.error('FATAL', e); process.exit(1); });
