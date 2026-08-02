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

  const browser = await chromium.launch({ headless: true, args: ['--no-sandbox', '--disable-blink-features=AutomationControlled'] });
  const context = await browser.newContext({
    viewport: { width: 1366, height: 900 },
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    locale: 'zh-CN',
  });
  await context.addCookies(cookies);
  const page = await context.newPage();

  console.log('[1] load x.com to grab queryId...');
  await page.goto('https://x.com/', { waitUntil: 'domcontentloaded', timeout: 30000 });
  await delay(4000);

  const qid = await page.evaluate(async () => {
    const sources = Array.from(document.querySelectorAll('script[src]')).map(s => s.src)
      .concat(Array.from(document.querySelectorAll('link[rel="preload"][as="script"]')).map(s => s.href));
    for (const src of sources) {
      if (/responsive-web|client-web/.test(src)) {
        try {
          const js = await (await fetch(src)).text();
          const m = js.match(/"UserTweets":"([a-zA-Z0-9_-]+)"/);
          if (m) return m[1];
        } catch (e) {}
      }
    }
    return null;
  });
  console.log('   queryId:', qid);
  if (!qid) { console.log('[!] no queryId found'); await browser.close(); process.exit(1); }

  const ct0 = cookies.find(c => c.name === 'ct0').value;
  const BEARER = 'AAAAAAAAAAAAAAAAAAAAAFQODgEAAAAAAN4o86drzE4yekuIa4pDU6rGo1i8BtYd96nYcXZx%2FQ';
  const features = {
    rweb_lists_timeline_redesign_enabled: true,
    responsive_web_graphql_exclude_directive_enabled: true,
    verified_phone_label_enabled: false,
    creator_subscriptions_tweet_preview_api_enabled: true,
    responsive_web_graphql_timeline_navigation_enabled: true,
    responsive_web_graphql_skip_user_profile_image_extensions_enabled: false,
    tweetypie_unmention_optimization_enabled: true,
    responsive_web_edit_tweet_api_enabled: true,
    graphql_is_translatable_rweb_tweet_is_translatable_enabled: true,
    view_counts_everywhere_api_enabled: true,
    longform_notetweets_consumption_enabled: true,
    responsive_web_twitter_article_tweet_consumption_enabled: false,
    tweet_averages_internal_enabled: false,
    freedom_of_speech_not_reach_fetch_enabled: true,
    standardized_nudges_misinfo: true,
    tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled: true,
    longform_notetweets_rich_text_read_enabled: true,
    longform_notetweets_inline_media_enabled: true,
    responsive_web_media_download_video_enabled: false,
    responsive_web_enhance_cards_enabled: false,
  };

  console.log('[2] fetching tweets via GraphQL...');
  const allTweets = [];
  let cursor = null;
  for (let p = 0; p < 6; p++) {
    const result = await page.evaluate(async (qid, cursor, ct0, BEARER, features) => {
      const variables = {
        userId: '1549259372101918721', count: 40, cursor,
        includePromotedContent: false,
        withQuickPromoteEligibilityTweetFields: true, withVoice: true, withV2Timeline: true,
      };
      const params = new URLSearchParams({ variables: JSON.stringify(variables), features: JSON.stringify(features) });
      const resp = await fetch(`https://x.com/i/api/graphql/${qid}/UserTweets?${params}`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${BEARER}`,
          'X-Csrf-Token': ct0,
          'X-Twitter-Auth-Type': 'OAuth2Session',
          'Content-Type': 'application/json',
        },
        credentials: 'include',
      });
      return await resp.json();
    }, qid, cursor, ct0, BEARER, features);

    let bottom = null, added = 0;
    try {
      const instr = result?.data?.user?.result?.timeline?.timeline?.instructions || [];
      for (const i of instr) {
        if (i.type === 'TimelineAddEntries') {
          for (const e of i.content.entries) {
            if (e.entryId && e.entryId.includes('tweet')) {
              try {
                const t = e.content.itemContent.tweet_results.result;
                allTweets.push({ text: t.legacy.full_text, time: t.legacy.created_at });
                added++;
              } catch (e2) {}
            } else if (e.content && e.content.cursorType === 'Bottom') {
              bottom = e.content.value;
            }
          }
        }
      }
    } catch (err) {
      console.log(`   parse err p${p}:`, (err.message || '').slice(0, 80));
      console.log('   resp:', JSON.stringify(result).slice(0, 200));
      break;
    }
    cursor = bottom;
    console.log(`   page ${p}: +${added} (total ${allTweets.length})`);
    if (!cursor || added === 0) break;
  }

  console.log(`\n[✓] GraphQL total: ${allTweets.length}`);
  fs.writeFileSync(`${WS}/data/conny_vv_tweets_gql.json`, JSON.stringify(allTweets, null, 2));
  console.log('saved -> data/conny_vv_tweets_gql.json');

  await browser.close();
})().catch(e => { console.error('FATAL', e); process.exit(1); });
