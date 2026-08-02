const { chromium } = require('playwright');
const fs = require('fs');

const COOKIE_FILE = 'F:/Users/Administrator/Documents/WorkBuddy/2026-07-24-21-36-14/conny_cookies.json';
const OUT = 'F:/Users/Administrator/Documents/WorkBuddy/2026-07-24-21-36-14/data/kaixintangtang_tweets.json';

(async () => {
  let cookies = JSON.parse(fs.readFileSync(COOKIE_FILE, 'utf-8'));
  cookies = cookies.map(c => {
    const o = { ...c };
    const sl = (o.sameSite || '').toLowerCase();
    if (sl === 'no_restriction' || sl === 'none') o.sameSite = 'None';
    else if (sl === 'lax') o.sameSite = 'Lax';
    else if (sl === 'strict') o.sameSite = 'Strict';
    else delete o.sameSite;
    if (o.expirationDate !== undefined) { o.expires = Math.floor(o.expirationDate); delete o.expirationDate; }
    delete o.storeId; delete o.hostOnly; delete o.session;
    return o;
  });
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({
    viewport: { width: 1280, height: 900 },
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36',
  });
  await ctx.addCookies(cookies);
  const page = await ctx.newPage();

  console.log('[nav] x.com/kaixintangtang');
  await page.goto('https://x.com/kaixintangtang', { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(6000);

  const loggedIn = await page.evaluate(() => !document.body.innerText.includes('Log in') && !document.body.innerText.includes('登录'));
  console.log('[auth] loggedIn =', loggedIn);

  const seen = new Map();
  async function collect() {
    const items = await page.evaluate(() => {
      const out = [];
      document.querySelectorAll('article').forEach(a => {
        const timeEl = a.querySelector('time');
        if (!timeEl) return;
        const dt = timeEl.getAttribute('datetime');
        const txt = (a.innerText || '').replace(/\s+/g, ' ').slice(0, 400);
        out.push({ datetime: dt, text: txt, raw: a.innerText.slice(0, 600) });
      });
      return out;
    });
    for (const it of items) {
      if (!it.datetime) continue;
      const key = it.datetime + '|' + it.text.slice(0, 40);
      if (!seen.has(key)) seen.set(key, it);
    }
    return items.length;
  }

  await collect();
  let lastCount = 0;
  for (let i = 0; i < 40; i++) {
    await page.evaluate(() => window.scrollBy(0, 2500));
    await page.waitForTimeout(1500);
    const n = await collect();
    if (seen.size === lastCount && i > 5) {
      if (i > 12) break;
    }
    lastCount = seen.size;
    if (i % 5 === 0) console.log(`[scroll ${i}] collected so far: ${seen.size}`);
  }

  const all = Array.from(seen.values());
  const years = {};
  all.forEach(t => { const y = (t.datetime || '').slice(0, 4); years[y] = (years[y] || 0) + 1; });
  console.log('TOTAL UNIQUE:', all.length);
  console.log('YEAR DIST:', JSON.stringify(years));
  console.log('DATE RANGE:', all.map(t => t.datetime).sort()[0], '->', all.map(t => t.datetime).sort().slice(-1)[0]);

  fs.writeFileSync(OUT, JSON.stringify(all, null, 2));
  console.log('[saved]', OUT);
  await browser.close();
})().catch(e => { console.error('FATAL', e); process.exit(1); });
