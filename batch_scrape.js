const { chromium } = require('playwright');
const fs = require('fs');

const WS = 'F:/Users/Administrator/Documents/WorkBuddy/2026-07-24-21-36-14';
const TARGETS = [
  'sunny31059',
  'sino11680908',
  'shutiaoniang',
  'jiajia2475',
  'chichi_maddy',
  'VulpesM',
  'wuuuuuucy',
  '5277888MCHS',
  'urlittlecuteboy'
];

const delay = ms => new Promise(r => setTimeout(r, ms));

(async () => {
  console.log('=== START BATCH SCRAPE ===');
  
  // 1. 加载 Cookie
  const raw = JSON.parse(fs.readFileSync(`${WS}/conny_cookies.json`, 'utf8'));
  const cookies = raw.map(c => ({
    name: c.name, value: c.value, domain: c.domain, path: c.path || '/',
    expires: c.expirationDate ? Math.floor(c.expirationDate) : undefined,
    httpOnly: c.httpOnly, secure: c.secure,
    sameSite: c.sameSite === 'no_restriction' ? 'None' : c.sameSite === 'lax' ? 'Lax' : c.sameSite === 'strict' ? 'Strict' : 'None',
  })).filter(c => c.name);

  // 2. 启动浏览器
  const browser = await chromium.launch({ 
    headless: true, 
    args: ['--disable-blink-features=AutomationControlled', '--no-sandbox'] 
  });
  
  const context = await browser.newContext({
    viewport: { width: 1366, height: 900 },
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    locale: 'zh-CN',
  });
  await context.addCookies(cookies);

  // 3. 循环采集
  for (const username of TARGETS) {
    console.log(`\n----------------------------------------`);
    console.log(`[+] Processing @${username}...`);
    const page = await context.newPage();
    
    try {
      await page.goto(`https://x.com/${username}`, { waitUntil: 'domcontentloaded', timeout: 35000 });
      await delay(5000);

      // 提取 Profile 信息
      console.log(`   Extracting profile...`);
      const profile = await page.evaluate(() => {
        const parseNum = (str) => {
          if (!str) return 0;
          str = str.replace(/[,，]/g, '').trim();
          if (str.includes('万') || str.includes('W')) {
            return Math.floor(parseFloat(str) * 10000);
          }
          if (str.toLowerCase().includes('k')) {
            return Math.floor(parseFloat(str) * 1000);
          }
          if (str.toLowerCase().includes('m')) {
            return Math.floor(parseFloat(str) * 1000000);
          }
          return parseInt(str, 10) || 0;
        };

        const result = {
          followers_count: 0,
          following_count: 0,
          tweet_count: 0,
          bio: '',
          is_sensitive: false
        };

        // 粉丝数 (X 中文有时是"关注者"，英文是"Followers")
        try {
          const links = Array.from(document.querySelectorAll('a[href*="/followers"], a[href*="/verified_followers"]'));
          for (const a of links) {
            const text = a.innerText || '';
            if (text.includes('关注者') || text.toLowerCase().includes('follower')) {
              const numSpan = a.querySelector('span');
              result.followers_count = parseNum(numSpan ? numSpan.innerText : text);
            } else if (text.includes('正在关注') || text.toLowerCase().includes('following')) {
              const numSpan = a.querySelector('span');
              result.following_count = parseNum(numSpan ? numSpan.innerText : text);
            }
          }
        } catch (e) {}

        // 发帖数
        try {
          const h2 = document.querySelector('h2[role="heading"]');
          if (h2 && h2.innerText && (h2.innerText.includes('贴子') || h2.innerText.includes('Posts'))) {
            // 例: "123 贴子"
            result.tweet_count = parseNum(h2.innerText);
          } else {
            const divs = Array.from(document.querySelectorAll('div'));
            const postDiv = divs.find(d => d.innerText && (d.innerText.endsWith('贴子') || d.innerText.endsWith('posts')));
            if (postDiv) result.tweet_count = parseNum(postDiv.innerText);
          }
        } catch (e) {}

        // Bio
        try {
          const bioEl = document.querySelector('[data-testid="UserDescription"]');
          if (bioEl) result.bio = bioEl.innerText.trim();
        } catch (e) {}

        // 敏感标记 (AppTab_Sensitive)
        const sensitiveEl = document.querySelector('[data-testid="AppTab_Sensitive"]');
        result.is_sensitive = sensitiveEl !== null;

        return result;
      });

      console.log(`   Profile result: followers=${profile.followers_count}, following=${profile.following_count}, posts=${profile.tweet_count}`);

      // 切换到 "最新/Latest" tab
      console.log(`   Switching to latest tab...`);
      const switched = await page.evaluate(() => {
        const tabs = Array.from(document.querySelectorAll('div[role="tab"], a[role="tab"], span'));
        const latest = tabs.find(t => /最新|Latest/.test(t.innerText || ''));
        if (latest) { latest.click(); return true; }
        return false;
      });
      await delay(3000);

      // 滚动抽取推文 - 循环滚动 20 次增量累加抓取推文并用 Map 去重的功能
      console.log(`   Scrolling and collecting tweets (incremental capture)...`);
      const tweetsMap = new Map();

      for (let i = 0; i < 20; i++) {
        await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
        await delay(2000); // 每次滚动 waitForTimeout 2秒等待加载，将 text 存入，防止首屏加载不完全时提取空

        const batch = await page.evaluate(() => {
          return Array.from(document.querySelectorAll('article[data-testid="tweet"]')).map(art => {
            try {
              const showBtn = Array.from(art.querySelectorAll('button, span')).find(el => {
                const text = el.innerText || '';
                return /显示|View/.test(text) && !/翻译|Translate/.test(text);
              });
              if (showBtn) showBtn.click();
            } catch (e) {}

            return {
              text: (art.querySelector('div[lang]')?.innerText || '').slice(0, 1500),
              time: art.querySelector('time')?.getAttribute('datetime') || '',
              replies: art.querySelector('[aria-label*="repl"], [aria-label*="回复"]')?.getAttribute('aria-label') || '',
              retweets: art.querySelector('[aria-label*="Retweet"], [aria-label*="转"]')?.getAttribute('aria-label') || '',
              likes: art.querySelector('[aria-label*="Like"], [aria-label*="喜欢"]')?.getAttribute('aria-label') || '',
              views: art.querySelector('[aria-label*="view"], [aria-label*="浏览"]')?.getAttribute('aria-label') || '',
              hasMedia: !!art.querySelector('img[data-testid="tweetPhoto"], video'),
              is_sensitive: !!(art.querySelector('[data-testid="AppTab_Sensitive"]') || art.querySelector('div[aria-label*="成人内容"], div[aria-label*="Sensitive"]')),
              raw: art.innerHTML || ''
            };
          }).filter(t => t.text.trim());
        });

        batch.forEach(t => {
          const key = t.text.replace(/\s+/g, '').slice(0, 100);
          if (key && !tweetsMap.has(key)) {
            tweetsMap.set(key, t);
          }
        });
      }

      const tweets = Array.from(tweetsMap.values());

      console.log(`   Unique tweets found: ${tweets.length}`);

      // 汇总写入文件
      const payload = {
        username: username,
        scraped_at: new Date().toISOString(),
        profile: {
          followers_count: profile.followers_count,
          following_count: profile.following_count,
          tweet_count: profile.tweet_count,
          bio: profile.bio,
          is_sensitive: profile.is_sensitive
        },
        recent_tweets: tweets.map(t => ({
          text: t.text,
          date: t.time,
          likes: t.likes,
          retweets: t.retweets,
          replies: t.replies,
          is_sensitive: t.is_sensitive,
          raw: t.raw
        })),
        account_status: {
          account_status: "normal"
        }
      };

      fs.writeFileSync(`${WS}/data/${username}_tweets.json`, JSON.stringify(payload, null, 2));
      console.log(`[✓] File saved: data/${username}_tweets.json`);

    } catch (e) {
      console.log(`[❌] Error processing @${username}:`, e.message);
    } finally {
      await page.close();
    }
  }

  await browser.close();
  console.log('\n=== BATCH SCRAPE COMPLETED ===');
})();
