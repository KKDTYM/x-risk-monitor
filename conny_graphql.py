import json, re, urllib.request, urllib.parse

WS = 'F:/Users/Administrator/Documents/WorkBuddy/2026-07-24-21-36-14'
cookies = json.load(open(f'{WS}/conny_cookies.json'))
cookie_header = "; ".join([f"{c['name']}={c['value']}" for c in cookies])
ct0 = next(c['value'] for c in cookies if c['name'] == 'ct0')
BEARER = "AAAAAAAAAAAAAAAAAAAAAFQODgEAAAAAAN4o86drzE4yekuIa4pDU6rGo1i8BtYd96nYcXZx%2FQ"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"

def http_get(url, headers):
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode('utf-8', 'replace')

# 1. get UserTweets queryId from web JS
print('[1] fetching queryId...')
html = http_get("https://x.com/", {"User-Agent": UA})
m = re.search(r'src="(https://abs\.twimg\.com/responsive-web/client-web-[^"]+\.js)"', html)
if not m:
    print('   JS url not found'); raise SystemExit(1)
js = http_get(m.group(1), {"User-Agent": UA})
qid = re.search(r'"UserTweets":"([a-zA-Z0-9_-]+)"', js)
if not qid:
    print('   queryId not found'); raise SystemExit(1)
print('   queryId:', qid.group(1))

headers = {
    "Authorization": f"Bearer {BEARER}",
    "X-Csrf-Token": ct0,
    "X-Twitter-Auth-Type": "OAuth2Session",
    "User-Agent": UA,
    "Referer": "https://x.com/Conny_vv",
    "Cookie": cookie_header,
    "Content-Type": "application/json",
    "Accept-Language": "zh-CN",
}

user_id = "1549259372101918721"
variables = {
    "userId": user_id, "count": 40, "cursor": None,
    "includePromotedContent": False,
    "withQuickPromoteEligibilityTweetFields": True,
    "withVoice": True, "withV2Timeline": True,
}
features = {
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
    "responsive_web_twitter_article_tweet_consumption_enabled": False,
    "tweet_averages_internal_enabled": False,
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
for page in range(5):
    variables["cursor"] = cursor
    params = urllib.parse.urlencode({"variables": json.dumps(variables), "features": json.dumps(features)})
    url = f"https://x.com/i/api/graphql/{qid.group(1)}/UserTweets?{params}"
    try:
        data = json.loads(http_get(url, headers))
    except Exception as e:
        print(f"   request failed page {page}:", e); break
    try:
        instr = data["data"]["user"]["result"]["timeline"]["timeline"]["instructions"]
    except Exception as e:
        print(f"   parse err page {page}:", str(e)[:100]); print(str(data)[:300]); break
    entries = []
    for i in instr:
        if i["type"] == "TimelineAddEntries":
            entries = i["content"]["entries"]
    new_count = 0
    for e in entries:
        if "tweet" in e.get("entryId", ""):
            try:
                t = e["content"]["itemContent"]["tweet_results"]["result"]
                txt = t["legacy"]["full_text"]
                created = t["legacy"]["created_at"]
                all_tweets.append({"text": txt, "time": created})
                new_count += 1
            except: pass
        elif e.get("content", {}).get("cursorType") == "Bottom":
            cursor = e["content"]["value"]
    print(f"   page {page}: +{new_count} (total {len(all_tweets)})")
    if not cursor or new_count == 0:
        break

print(f"\n[✓] TOTAL via GraphQL: {len(all_tweets)}")
json.dump(all_tweets, open(f'{WS}/data/conny_vv_tweets_gql.json', 'w'), ensure_ascii=False, indent=2)
print("saved to data/conny_vv_tweets_gql.json")
