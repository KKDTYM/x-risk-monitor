import json, re, urllib.request, urllib.parse, urllib.error

BASE = "F:/Users/Administrator/Documents/WorkBuddy/2026-07-24-21-36-14"
UID = "1549259372101918721"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
BEARER = "AAAAAAAAAAAAAAAAAAAAAFQODgEAAAAAAN4o86drzE4yekuIa4pDU6rGo1i8BtYd96nYcXZx%2FQ"

def req(url, headers, data=None, method=None):
    r = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(r, timeout=30) as resp:
        return resp.read().decode("utf-8", "replace")

# 1. guest token (POST)
try:
    gt_raw = req("https://api.x.com/1.1/guest/activate.json",
                 {"Authorization": f"Bearer {BEARER}", "Content-Type": "application/json", "User-Agent": UA},
                 data=b"{}", method="POST")
    GTOK = json.loads(gt_raw).get("guest_token")
    print("guest_token:", GTOK)
except Exception as e:
    print("guest token FAILED:", e)
    GTOK = None

# 2. queryId
query_id = None
try:
    html = req("https://x.com/", {"User-Agent": UA})
    m = re.search(r'src="(https://abs\.twimg\.com/responsive-web/client-web-[^"]+\.js)"', html)
    if m:
        js = req(m.group(1), {"User-Agent": UA})
        q = re.search(r'"UserTweets":"([a-zA-Z0-9_-]+)"', js)
        if q:
            query_id = g.group(1)
except Exception as e:
    print("queryId fetch err:", e)

if not query_id:
    try:
        query_id = open(f"{BASE}/conny_queryid.txt").read().strip()
    except Exception:
        query_id = None
print("query_id:", query_id)

if not (GTOK and query_id):
    print("CANNOT PROCEED without guest token + query id")
    raise SystemExit(1)

# 3. call GraphQL UserTweets
variables = {
    "userId": UID, "count": 40, "cursor": None,
    "includePromotedContent": True, "withQuickPromoteEligibilityTweetFields": True,
    "withVoice": True, "withV2Timeline": True
}
features = {
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
    "tweet_a_highlighted_tweet_rweb_tweet_is_highlighted_enabled": True,
    "freedom_of_speech_not_reach_fetch_enabled": True,
    "standardized_nudges_misinfo": True,
    "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": True,
    "longform_notetweets_rich_text_read_enabled": True,
    "longform_notetweets_inline_media_enabled": True,
    "responsive_web_media_download_video_enabled": False,
    "responsive_web_enhance_cards_enabled": False
}
params = urllib.parse.urlencode({
    "variables": json.dumps(variables),
    "features": json.dumps(features)
})
url = f"https://x.com/i/api/graphql/{query_id}/UserTweets?{params}"
headers = {
    "Authorization": f"Bearer {BEARER}",
    "X-Guest-Token": GTOK,
    "User-Agent": UA,
    "Content-Type": "application/json",
    "X-Twitter-Client-Language": "en",
    "X-Twitter-Active-User": "yes",
    "Referer": f"https://x.com/{''}"
}
try:
    body = req(url, headers)
    data = json.loads(body)
except Exception as e:
    print("GraphQL call FAILED:", e)
    raise SystemExit(1)

# 4. parse
tweets = []
def walk(o):
    if isinstance(o, dict):
        if "tweetResult" in o or "tweet_results" in o:
            res = o.get("tweetResult") or o.get("tweet_results")
            tw = (res or {}).get("result") if isinstance(res, dict) else None
            if isinstance(tw, dict) and tw.get("__typename") == "Tweet":
                leg = tw.get("legacy", {})
                core = tw.get("core", {})
                text = leg.get("full_text", "")
                if text:
                    tweets.append({
                        "text": text,
                        "likes": int(leg.get("favorite_count") or 0),
                        "retweets": int(leg.get("retweet_count") or 0),
                        "is_retweet": bool(leg.get("retweeted")),
                        "is_sensitive": bool(leg.get("possibly_sensitive") or tw.get("possibly_sensitive")),
                        "created_at": leg.get("created_at", "")
                    })
        for v in o.values():
            walk(v)
    elif isinstance(o, list):
        for v in o:
            walk(v)

walk(data)
print("PARSED tweets:", len(tweets))
# save profile from fxtwitter + tweets
profile = {}
try:
    fx = json.load(open(f"{BASE}/data/conny_vv_fxtwitter.json"))
    u = fx.get("user", {})
    profile = {
        "name": u.get("name"), "description": u.get("description"),
        "followers_count": u.get("followers"), "following_count": u.get("following"),
        "tweets_count": u.get("tweets"), "location": u.get("location"),
        "joined": u.get("joined"), "is_sensitive": False, "protected": bool(u.get("protected"))
    }
except Exception as e:
    print("profile err", e)

out = {"username": "Conny_vv", "account_status": "normal", "is_sensitive": False,
       "profile": profile, "recent_tweets": tweets}
json.dump(out, open(f"{BASE}/conny_vv_data.json", "w"), ensure_ascii=False, indent=2)
print("SAVED conny_vv_data.json with", len(tweets), "tweets")
for t in tweets[:5]:
    print("-", t["text"][:60].replace("\n"," "), "| likes", t["likes"], "rt", t["retweets"], "sens", t["is_sensitive"])
