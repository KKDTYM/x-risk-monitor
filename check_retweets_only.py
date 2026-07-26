"""
直接从已有 syndication_raw.txt 加载推文数据 + Playwright 逐个检查"已转帖"标记
"""
import json
import re
from datetime import datetime

def load_syndication_tweets(username):
    """从 syndication_raw 文件加载推文"""
    import html as html_mod
    
    filepath = f'F:/Users/Administrator/Documents/WorkBuddy/2026-07-24-21-36-14/data/syndication_raw_{username}.txt'
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            raw_html = f.read()
    except FileNotFoundError:
        # 尝试不带用户名的文件名
        filepath = 'F:/Users/Administrator/Documents/WorkBuddy/2026-07-24-21-36-14/data/syndication_raw.txt'
        with open(filepath, 'r', encoding='utf-8') as f:
            raw_html = f.read()
    
    nx_idx = raw_html.find('__NEXT_DATA__')
    if nx_idx < 0:
        print("找不到 __NEXT_DATA__")
        return None
    
    json_start = raw_html.find('{', nx_idx)
    depth = 0
    json_end = json_start
    for i in range(json_start, len(raw_html)):
        if raw_html[i] == '{':
            depth += 1
        elif raw_html[i] == '}':
            depth -= 1
            if depth == 0:
                json_end = i
                break
    
    if depth != 0:
        print("JSON 未闭合")
        return None
    
    json_str = raw_html[json_start:json_end+1]
    data = json.loads(json_str)
    
    entries = data['props']['pageProps']['timeline']['entries']
    tweets = []
    
    for entry in entries:
        tweet_data = entry.get('content', {}).get('tweet', {})
        if not tweet_data:
            continue
        
        full_text = tweet_data.get('full_text', '')
        try:
            decoded = full_text.encode('latin1').decode('utf-8')
        except:
            decoded = full_text
        decoded = decoded.replace('\\n', '\n').replace('\\t', ' ')
        
        tweets.append({
            'id_str': tweet_data.get('id_str', ''),
            'text': decoded,
            'created_at': tweet_data.get('created_at', ''),
            'possibly_sensitive': tweet_data.get('possibly_sensitive', False),
            'entities': tweet_data.get('entities', {}),
            'extended_entities': tweet_data.get('extended_entities', {}),
        })
    
    return tweets


def check_retweet_with_playwright(screen_name, tweet_id):
    """用 Playwright 访问单条推文，检查'已转帖'标记"""
    from playwright.sync_api import sync_playwright
    
    cookies_path = 'F:/Users/Administrator/Documents/WorkBuddy/2026-07-24-21-36-14/conny_cookies.json'
    with open(cookies_path, 'r') as f:
        cookies = json.load(f)
    
    result = {
        'is_retweet': False,
        'retweet_author': '',
        'error': ''
    }
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                executable_path='C:\\Users\\Administrator\\AppData\\Local\\ms-playwright\\chromium-1228\\chrome-win64\\chrome.exe'
            )
            
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                cookies=cookies
            )
            
            page = context.new_page()
            page.goto(f'https://x.com/{screen_name}/status/{tweet_id}', wait_until='domcontentloaded', timeout=15000)
            page.wait_for_timeout(2000)
            
            retweet_info = page.evaluate('''(screenName) => {
                const result = { isRetweet: false, retweetAuthor: '' };
                const allElements = document.querySelectorAll('*');
                for (const el of allElements) {
                    const text = el.innerText || '';
                    if (text.includes('已转帖') || text.includes('Reposted')) {
                        result.isRetweet = true;
                        const userLinks = el.querySelectorAll('a[href*="/"]');
                        for (const link of userLinks) {
                            const href = link.href || '';
                            const m = href.match(/x\\.com\\/([A-Za-z0-9_\\-]+)/);
                            if (m && m[1] !== screenName) {
                                result.retweetAuthor = m[1];
                            }
                        }
                        break;
                    }
                }
                return result;
            }''', screen_name)
            
            result['is_retweet'] = retweet_info.get('isRetweet', False)
            result['retweet_author'] = retweet_info.get('retweetAuthor', '')
            
            browser.close()
    except Exception as e:
        result['error'] = str(e)
    
    return result


def main():
    username = 'sensechiori'
    print(f"从文件加载 @{username} 的推文数据...")
    tweets = load_syndication_tweets(username)
    
    if not tweets:
        print("加载失败")
        return
    
    print(f"加载到 {len(tweets)} 条推文")
    
    # 逐个检查
    print("\n开始逐个检查'已转帖'标记...")
    print("(每条约需 3-5 秒，共约 {} 秒)".format(len(tweets) * 4))
    
    retweet_count = 0
    original_count = 0
    
    for i, tweet in enumerate(tweets):
        tweet_id = tweet['id_str']
        print(f"[{i+1}/{len(tweets)}] 检查 {tweet_id}...")
        
        check = check_retweet_with_playwright(username, tweet_id)
        
        tweet['is_retweet'] = check['is_retweet']
        tweet['retweet_author'] = check['retweet_author']
        tweet['playwright_error'] = check['error']
        
        if check['is_retweet']:
            retweet_count += 1
            print(f"  ** 转贴! 来自 @{check['retweet_author']}")
        else:
            original_count += 1
    
    print(f"\n=== 统计 ===")
    print(f"原创: {original_count}")
    print(f"转贴: {retweet_count}")
    
    output = {
        'username': username,
        'scraped_at': datetime.now().isoformat(),
        'source': 'syndication_file_plus_playwright_retweet_check',
        'total_count': len(tweets),
        'original_count': original_count,
        'retweet_count': retweet_count,
        'tweets': tweets
    }
    
    output_path = f'F:/Users/Administrator/Documents/WorkBuddy/2026-07-24-21-36-14/data/{username}_retweet_checked.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"\n保存: {output_path}")


if __name__ == '__main__':
    main()
