const { chromium } = require('playwright');
const fs = require('fs');

const WS = 'F:/Users/Administrator/Documents/WorkBuddy/2026-07-24-21-36-14';
const TARGET = 'Conny_vv';
const DEBUG = `${WS}/conny_debug_cookies`;

if (!fs.existsSync(DEBUG)) fs.mkdirSync(DEBUG, { recursive: true });
const save = (n, b) => fs.writeFileSync(`${DEBUG}/${n}.png`, b);
const delay = ms => new Promise(r => setTimeout(r, ms));

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

  console.log('[1] goto @Conny_vv');
  await page.goto(`https://x.com/${TARGET}`, { waitUntil: 'domcontentloaded', timeout: 30000 });
  await delay(5000);

  // Try switching to "Latest" (最新) tab if present — more complete for old accounts
  const switched = await page.evaluate(() => {
    const tabs = Array.from(document.querySelectorAll('div[role="tab"], a[role="tab"], span'));
    const latest = tabs.find(t => /最新|Latest/.test(t.innerText || ''));
    if (latest) { latest.click(); return true; }
    return false;
  });
  console.log('   switched to Latest tab:', switched);
  await delay(4000);

  // Scroll-to-bottom + cross-batch dedup
  console.log('[2] scroll + dedup scrape...');
  const seen = new Set();
  const tweets = [];
  let stable = 0;
  for (let i = 0; i < 45; i++) {
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
    await delay(2200);
    const batch = await page.evaluate(() => {
      return Array.from(document.querySelectorAll('article[data-testid="tweet"]')).map(art => ({
        text: (art.querySelector('div[lang]')?.innerText || '').slice(0, 1500),
        time: art.querySelector('time')?.getAttribute('datetime') || '',
        replies: art.querySelector('[aria-label*="repl"], [aria-label*="回复"]')?.getAttribute('aria-label') || '',
        retweets: art.querySelector('[aria-label*="Retweet"], [aria-label*="转"]')?.getAttribute('aria-label') || '',
        likes: art.querySelector('[aria-label*="Like"], [aria-label*="喜欢"]')?.getAttribute('aria-label') || '',
        views: art.querySelector('[aria-label*="view"], [aria-label*="浏览"]')?.getAttribute('aria-label') || '',
        hasMedia: !!art.querySelector('img[data-testid="tweetPhoto"], video'),
      })).filter(t => t.text.trim());
    });
    let added = 0;
    batch.forEach(t => {
      const key = t.text.replace(/\s+/g, '').slice(0, 80);
      if (!seen.has(key)) { seen.add(key); tweets.push(t); added++; }
    });
    if ((i + 1) % 4 === 0 || added > 0) console.log(`   scroll ${i + 1}: +${added} new (total ${tweets.length})`);
    if (added === 0) { stable++; if (stable >= 4) { console.log('   (stable — stopping)'); break; } }
    else stable = 0;
  }

  console.log(`\n[✓] Total unique tweets: ${tweets.length}`);
  fs.writeFileSync(`${WS}/data/conny_vv_tweets.json`, JSON.stringify(tweets, null, 2));

  // Date range
  const dates = tweets.map(t => t.time).filter(Boolean).sort();
  console.log('   date range:', dates[0] || '?', '→', dates[dates.length - 1] || '?');

  console.log('\n--- PREVIEW (first 15) ---');
  tweets.slice(0, 15).forEach((t, i) => {
    console.log(`\n[${i + 1}] ${t.time || '?'} | ❤️${t.likes} 🔁${t.retweets} | media:${t.hasMedia}`);
    console.log(t.text.slice(0, 200).replace(/\n/g, ' '));
  });

  await browser.close();
  console.log('\n=== DONE ✓ ===');
})().catch(e => { console.error('FATAL', e); process.exit(1); });
