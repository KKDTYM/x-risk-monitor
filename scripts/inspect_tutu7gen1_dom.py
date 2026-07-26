"""
检查 @tutu7gen1 页面 DOM 结构，找到推文链接的真实格式
"""
import json
import time
from playwright.sync_api import sync_playwright

PROJECT_DIR = r'F:\Users\Administrator\Documents\WorkBuddy\2026-07-24-21-36-14'

COOKIES = [
    {"domain": ".x.com", "expirationDate": 1816600103.098764, "hostOnly": False, "httpOnly": True, "name": "auth_token", "path": "/", "sameSite": "no_restriction", "secure": True, "session": False, "storeId": None, "value": "0555da63fcf228b97af5aec8c8ed4fd6d5841880"},
    {"domain": ".x.com", "expirationDate": 1819618477.028269, "hostOnly": False, "httpOnly": False, "name": "guest_id", "path": "/", "sameSite": "no_restriction", "secure": True, "session": False, "storeId": None, "value": "v1%3A178505847748990053"},
    {"domain": ".x.com", "expirationDate": 1819618476.635722, "hostOnly": False, "httpOnly": False, "name": "ads_prefs", "path": "/", "sameSite": "no_restriction", "secure": True, "session": False, "storeId": None, "value": "\"HBIRAAA=\""},
    {"domain": ".x.com", "expirationDate": 1816600258.465055, "hostOnly": False, "httpOnly": False, "name": "twid", "path": "/", "sameSite": "no_restriction", "secure": True, "session": False, "storeId": None, "value": "u%3D2081335439026421760"},
    {"domain": ".x.com", "hostOnly": False, "httpOnly": True, "name": "_twitter_sess", "path": "/", "sameSite": None, "secure": True, "session": True, "storeId": None, "value": "BAh7BiIKZmxhc2hJQzonQWN0aW9uQ29udHJvbGxlcjo6Rmxhc2g6OkZsYXNo%250ASGFzaHsABjoKQHVzZWR7AA%253D%253D--1164b91ac812d853b877e93ddb612b7471bebc74"},
    {"domain": ".x.com", "expirationDate": 1819624250.480158, "hostOnly": False, "httpOnly": True, "name": "auth_multi", "path": "/", "sameSite": "lax", "secure": True, "session": False, "storeId": None, "value": "\"497862683:443bd09a5c16b0d8e346459f52686dc7be306564|1919756553915428864:a40bfcf10aa9fda18b4e1768fc6d63e567a9e5fc|1969781334114455552:3fe146efd1cc10b8179ef91e36f583d60a5c6e5b\""},
    {"domain": ".x.com", "expirationDate": 1785065063.405039, "hostOnly": False, "httpOnly": True, "name": "__cf_bm", "path": "/", "sameSite": "no_restriction", "secure": True, "session": False, "storeId": None, "value": "gC8t1L9RsF3ndSQTlNW44GTP2fH6WB_86U2pvCjlV0U-1785063263.959605-1.0.1.1-D4toXEYknP5RJOyGlG4sM_HGw_2jhgUL6VTmOmum3utpnst26y3miE8TIaLHHRcRuu3qv8JqEVPNwzCXxdysjZc5qHIsdtkUpC0.rWlSzPWSCfviWn93gZVSUwcOiu3D"},
    {"domain": ".x.com", "expirationDate": 1819624103.742303, "hostOnly": False, "httpOnly": False, "name": "ct0", "path": "/", "sameSite": "lax", "secure": True, "session": False, "storeId": None, "value": "bb33543802aefbd7f6b2496ef8ec78ec578d22decbc0b5a0fa2ff1d66846a7a57deff1cc2b0fbc16f7e3edb3b2bcb9b0758b128c9af16bf0133c44980671ba5f329812ffb971fdd03443edf83423e4ee"},
    {"domain": ".x.com", "expirationDate": 1819624249.835153, "hostOnly": False, "httpOnly": False, "name": "guest_id_ads", "path": "/", "sameSite": "no_restriction", "secure": True, "session": False, "storeId": None, "value": "v1%3A178505847748990053"},
    {"domain": ".x.com", "expirationDate": 1819624249.835252, "hostOnly": False, "httpOnly": False, "name": "guest_id_marketing", "path": "/", "sameSite": "no_restriction", "secure": True, "session": False, "storeId": None, "value": "v1%3A178505847748990053"},
    {"domain": ".x.com", "expirationDate": 1819624103.098585, "hostOnly": False, "httpOnly": True, "name": "kdt", "path": "/", "sameSite": None, "secure": True, "session": False, "storeId": None, "value": "I26qcLfGtmQPKocgpIA1CmOPLRiS2kYQu8CY2vdA"},
    {"domain": ".x.com", "expirationDate": 1819609695.890338, "hostOnly": False, "httpOnly": False, "name": "personalization_id", "path": "/", "sameSite": "no_restriction", "secure": True, "session": False, "storeId": None, "value": "\"v1_VF7XpjNa6DEkBMUivBb/xQ==\""},
]


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    
    context = browser.new_context(
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
        viewport={'width': 1920, 'height': 1080}
    )
    
    for c in COOKIES:
        cookie = {
            'name': c['name'],
            'value': c['value'],
            'domain': c['domain'],
            'path': c.get('path', '/'),
        }
        if c.get('expirationDate'):
            cookie['expires'] = int(c['expirationDate'])
        context.add_cookies([cookie])
    
    page = context.new_page()
    
    print('访问 @tutu7gen1 主页...')
    try:
        page.goto('https://x.com/tutu7gen1', wait_until='domcontentloaded', timeout=30000)
        time.sleep(8)
    except Exception as e:
        print(f'加载超时: {e}')
    
    # 滚动加载更多内容
    print('滚动页面...')
    for i in range(10):
        page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
        time.sleep(2)
    
    # 提取所有包含数字链接（可能是推文）
    tweet_links = page.locator('a[href*="/tutu7gen1/"]').all()
    print(f'找到 /tutu7gen1/ 链接: {len(tweet_links)} 条')
    
    # 提取所有 href 属性包含数字的链接
    all_links = page.evaluate('''() => {
        const links = Array.from(document.querySelectorAll('a[href]'));
        return links
            .filter(l => {
                const href = l.getAttribute('href') || '';
                return href.match(/\\/\\d+/) && !href.includes('settings') && !href.includes('media');
            })
            .slice(0, 20)
            .map(l => l.getAttribute('href'));
    }''')
    
    print(f'\n提取到的链接示例:')
    for link in all_links[:10]:
        print(f'  {link}')
    
    # 尝试获取推文内容
    articles = page.locator('article').all()
    print(f'\n找到 article 元素: {len(articles)} 个')
    
    if articles:
        print('\n第一个 article 内容:')
        first_article = articles[0]
        text = first_article.inner_text()
        print(f'Text length: {len(text)}')
        print(f'Text (first 500 chars):\n{text[:500]}')
        
        hrefs = first_article.locator('a').all()
        print(f'\nLinks in first article: {len(hrefs)}')
        for h in hrefs[:5]:
            print(f'  {h.get_attribute("href", timeout=1000)}')
    
    # 保存完整 HTML
    html = page.content()
    with open(f'{PROJECT_DIR}/data/tutu7gen1_dom.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'\n完整 HTML 已保存到 {PROJECT_DIR}/data/tutu7gen1_dom.html')
    
    browser.close()
