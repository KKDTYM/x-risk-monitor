"""
批量抓取监控账号的推文 + 识别转推标记
支持: @dangao0709, @kaixintangtang
"""
import json
import re
import os
from datetime import datetime
from playwright.sync_api import sync_playwright

BASE_DIR = r'F:\Users\Administrator\Documents\WorkBuddy\2026-07-24-21-36-14'
DATA_DIR = os.path.join(BASE_DIR, 'data')
COOKIES_PATH = os.path.join(BASE_DIR, 'conny_cookies.json')

ACCOUNTS = ['dangao0709', 'kaixintangtang']


def load_syndication_tweets(username):
    """从 syndication_raw 文件加载推文"""
    filepath = os.path.join(DATA_DIR, f'syndication_raw_{username}.txt')
    if not os.path.exists(filepath):
        print(f"  ✗ {username}: 未找到 syndication_raw_{username}.txt")
        return None
    
    with open(filepath, 'r', encoding='utf-8') as f:
        raw_html = f.read()
    
    nx_idx = raw_html.find('__NEXT_DATA__')
    if nx_idx < 0:
        print(f"  ✗ {username}: 找不到 __NEXT_DATA__")
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
        print(f"  ✗ {username}: JSON 未闭合")
        return None
    
    json_str = raw_html[json_start:json_end+1]
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        print(f"  ✗ {username}: JSON 解析失败: {e}")
        return None
    
    entries = data.get('props', {}).get('pageProps', {}).get('timeline', {}).get('entries', [])
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
    try:
        with open(COOKIES_PATH, 'r') as f:
            cookies = json.load(f)
    except:
        return {'is_retweet': False, 'retweet_author': '', 'error': 'Cookie加载失败'}
    
    result = {
        'is_retweet': False,
        'retweet_author': '',
        'error': ''
    }
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                executable_path=r'C:\Users\Administrator\AppData\Local\ms-playwright\chromium-1228\chrome-win64\chrome.exe'
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


def process_account(username):
    """处理单个账号"""
    print(f"\n{'='*60}")
    print(f"处理 @{username}")
    print(f"{'='*60}")
    
    tweets = load_syndication_tweets(username)
    if not tweets:
        print(f"  ✗ {username}: 加载失败，跳过")
        return None
    
    print(f"  ✓ 加载到 {len(tweets)} 条推文")
    
    # 逐个检查转推
    print(f"\n  开始逐个检查'已转帖'标记...")
    print(f"  (每条约需 3-5 秒，共约 {len(tweets) * 4} 秒)")
    
    retweet_count = 0
    original_count = 0
    error_count = 0
    
    for i, tweet in enumerate(tweets):
        tweet_id = tweet['id_str']
        if i % 10 == 0:
            print(f"  [{i+1}/{len(tweets)}] 已检查 {retweet_count} 转推, {original_count} 原创, {error_count} 错误")
        
        check = check_retweet_with_playwright(username, tweet_id)
        
        tweet['is_retweet'] = check['is_retweet']
        tweet['retweet_author'] = check['retweet_author']
        tweet['playwright_error'] = check['error']
        
        if check['error']:
            error_count += 1
        elif check['is_retweet']:
            retweet_count += 1
            print(f"    ** 转贴! 来自 @{check['retweet_author']} (推文 {tweet_id[:12]}...)")
        else:
            original_count += 1
    
    print(f"\n  {'='*60}")
    print(f"  @{username} 统计结果:")
    print(f"  原创: {original_count}")
    print(f"  转贴: {retweet_count}")
    print(f"  错误: {error_count}")
    print(f"  总计: {len(tweets)}")
    
    if len(tweets) > 0:
        rt_ratio = retweet_count / len(tweets)
        print(f"  转贴占比: {rt_ratio:.1%}")
    
    output = {
        'username': username,
        'scraped_at': datetime.now().isoformat(),
        'source': 'syndication_file_plus_playwright_retweet_check',
        'total_count': len(tweets),
        'original_count': original_count,
        'retweet_count': retweet_count,
        'error_count': error_count,
        'retweet_ratio': retweet_count / len(tweets) if len(tweets) > 0 else 0,
        'tweets': tweets
    }
    
    output_path = os.path.join(DATA_DIR, f'{username}_retweet_checked.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"  保存: {output_path}")
    
    return output


def main():
    print("X账号转贴批量抓取工具")
    print(f"目标账号: {', '.join('@' + a for a in ACCOUNTS)}")
    
    results = []
    for account in ACCOUNTS:
        result = process_account(account)
        if result:
            results.append(result)
    
    if results:
        print(f"\n{'='*60}")
        print("所有账号处理完成！")
        print(f"{'='*60}")
    else:
        print("\n✗ 没有账号处理成功")


if __name__ == '__main__':
    main()
