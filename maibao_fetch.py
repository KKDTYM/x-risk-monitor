import json, re, urllib.request, urllib.parse, sys

WS = 'F:/Users/Administrator/Documents/WorkBuddy/2026-07-24-21-36-14'
HANDLE = sys.argv[1] if len(sys.argv) > 1 else "Maibao1998"
PAGES = int(sys.argv[2]) if len(sys.argv) > 2 else 6
COOKIE_FILE = f'{WS}/conny_cookies.json'

cookies = json.load(open(COOKIE_FILE, encoding='utf-8'))
cookie_header = "; ".join([f"{c['name']}={c['value']}" for c in cookies])
ct0 = next(c['value'] for c in cookies if c['name'] == 'ct0')
BEARER = "AAAAAAAAAAAAAAAAAAAAAFQODgEAAAAAAN4o86drzE4yekuIa4pDU6rGo1i8BtYd96nYcXZx%2FQ"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"

def http_get(url, headers):
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode('utf-8', 'replace')

def get_legacy(t):
    if not isinstance(t, dict): return None
    if 'legacy' in t: return t['legacy']
    if isinstance(t.get('tweet'), dict) and 'legacy' in t['tweet']:
        return t['tweet']['legacy']
    return None

print('[1] fetch page + extract queryIds from main.js...')
html = http_get(f"https://x.com/{HANDLE}", {"User-Agent": UA, "Cookie": cookie_header, "Accept-Language": "zh-CN"})
mjs = re.search(r'(https://abs\.twimg\.com/responsive-web/client-web/main\.[a-f0-9]+\.js)', html)
if not mjs:
    print('   [!] main.js not found in page'); sys.exit(1)
js = http_get(mjs.group(1), {"User-Agent": UA, "Cookie": cookie_header})
qids = {}
for op in ('UserByScreenName', 'UserTweets'):
    q = re.search(rf'queryId:"([a-zA-Z0-9_-]+)",operationName:"{op}"', js)
    if q:
        qids[op] = g = q.group(1)
        print(f'   {op}: {g}')
    else:
        print(f'   [!] {op} queryId not found'); sys.exit(1)

base_headers = {
    "Authorization": f"Bearer {BEARER}",
    "X-Csrf-Token": ct0,
    "X-Twitter-Auth-Type": "OAuth2Session",
    "X-Twitter-Active-User": "yes",
    "User-Agent": UA,
    "Referer": f"https://x.com/{HANDLE}",
    "Origin": "https://x.com",
    "Cookie": cookie_header,
    "Content-Type": "application/json",
    "Accept-Language": "zh-CN",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
}

# ---- resolve numeric userId ----
print(f'[2] resolving userId for @{HANDLE}...')
variables = {"screen_name": HANDLE, "withHighlightedLabel": True}
features = {"hidden_profile_subscriptions_enabled": True, "rweb_tipjar_consumption_enabled": True,
            "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
            "responsive_web_home_pinned_timelines_enabled": True,
            "responsive_web_twitter_article_tweet_consumption_enabled": False}
params = urllib.parse.urlencode({"variables": json.dumps(variables), "features": json.dumps(features)})
url = f"https://x.com/i/api/graphql/{qids['UserByScreenName']}/UserByScreenName?{params}"
try:
    data = json.loads(http_get(url, base_headers))
    user = data["data"]["user"]["result"]
    user_id = user["rest_id"]
    uname = user["legacy"]["name"]
    followers = user["legacy"]["followers_count"]
    following = user["legacy"]["friends_count"]
    bio = user["legacy"]["description"]
    print(f'   userId={user_id} name={uname} followers={followers} following={following}')
except Exception as e:
    print('   [!] resolve failed:', str(e)[:200])
    print('   raw:', str(data)[:300] if 'data' in dir() else '')
    sys.exit(1)

# ---- fetch tweets ----
print(f'[3] fetching tweets (max {PAGES} pages)...')
features2 = {
    "rweb_lists_timeline_redesign_enabled": True,
    "responsive_web_graphql_exclude_directive_enabled": True,
    "verified_phone_label_enabled": False,
    "creator_subscriptions_tweet_preview_api_enabled": True,
    "responsive_web_graphql_timeline_navigation_enabled": True,
    "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
    "tweetypie_unmention_optimization_enabled": True,
    "responsive_web_edit_tweet_api_enabled": True,
    "graphql_is_translatable_rweb_tweet_is_translatable_enabled": True,
    "view_counts_everywhere_api_enabled": True,
    "longform_notetweets_consumption_enabled": True,
    "freedom_of_speech_not_reach_fetch_enabled": True,
    "standardized_nudges_misinfo": True,
    "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": True,
    "longform_notetweets_rich_text_read_enabled": True,
    "longform_notetweets_inline_media_enabled": True,
    "responsive_web_media_download_video_enabled": False,
    "responsive_web_enhance_cards_enabled": False,
}
all_tweets = []
cursor = None
for page in range(PAGES):
    variables2 = {
        "userId": user_id, "count": 40, "cursor": cursor,
        "includePromotedContent": False,
        "withQuickPromoteEligibilityTweetFields": True,
        "withVoice": True, "withV2Timeline": True,
    }
    params = urllib.parse.urlencode({"variables": json.dumps(variables2), "features": json.dumps(features2)})
    url = f"https://x.com/i/api/graphql/{qids['UserTweets']}/UserTweets?{params}"
    try:
        d = json.loads(http_get(url, base_headers))
    except Exception as e:
        print(f'   request failed page {page}:', e); break
    try:
        instr = d["data"]["user"]["result"]["timeline"]["timeline"]["instructions"]
    except Exception as e:
        print(f'   parse err page {page}:', str(e)[:120]); print(str(d)[:300]); break
    entries = []
    for i in instr:
        if i.get("type") == "TimelineAddEntries":
            entries = i["content"]["entries"]
    new_count = 0
    for e in entries:
        if "tweet" in e.get("entryId", ""):
            try:
                t = e["content"]["itemContent"]["tweet_results"]["result"]
                leg = get_legacy(t)
                if not leg: continue
                media_urls = []
                for m in leg.get("entities", {}).get("media", []):
                    media_urls.append(m.get("media_url_https", ""))
                for u in leg.get("entities", {}).get("urls", []):
                    media_urls.append(u.get("expanded_url", ""))
                raw = leg.get("full_text", "") + " " + " ".join([x for x in media_urls if x])
                tw = {
                    "text": leg.get("full_text", ""),
                    "time": leg.get("created_at", ""),
                    "is_retweet": bool(leg.get("retweeted_status_id_str")),
                    "is_sensitive": leg.get("possibly_sensitive", False),
                    "possibly_sensitive": leg.get("possibly_sensitive", False),
                    "likes": int(leg.get("favorite_count", 0) or 0),
                    "retweets": int(leg.get("retweet_count", 0) or 0),
                    "url": f"https://x.com/{HANDLE}/status/{leg.get('id_str','')}",
                    "raw": raw,
                    "has_media": bool(media_urls),
                }
                all_tweets.append(tw)
                new_count += 1
            except Exception:
                pass
        elif e.get("content", {}).get("cursorType") == "Bottom":
            cursor = e["content"]["value"]
    print(f'   page {page}: +{new_count} (total {len(all_tweets)})')
    if not cursor or new_count == 0:
        break

print(f"\n[✓] TOTAL: {len(all_tweets)} tweets for @{HANDLE}")
media_cnt = sum(1 for t in all_tweets if t["has_media"])
print(f"   with media: {media_cnt} | sensitive-flagged: {sum(1 for t in all_tweets if t['is_sensitive'])}")

out = {
    "profile": {
        "handle": f"@{HANDLE}", "name": uname, "bio": bio,
        "followers_count": followers, "following_count": following,
        "user_id": user_id,
    },
    "tweets": all_tweets,
}
json.dump(out, open(f'{WS}/data/{HANDLE.lower()}_raw.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print(f"saved to data/{HANDLE.lower()}_raw.json")
