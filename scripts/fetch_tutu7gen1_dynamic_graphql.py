"""
从页面动态获取 GraphQL query ID 并请求推文
"""
import json
import re
import time
import requests
from playwright.sync_api import sync_playwright
from datetime import datetime

PROJECT_DIR = r'F:\Users\Administrator\Documents\WorkBuddy\2026-07-24-21-36-14'
DATA_DIR = f'{PROJECT_DIR}/data'

COOKIES_STR = '; '.join([
    "auth_token=0555da63fcf228b97af5aec8c8ed4fd6d5841880",
    "guest_id=v1%3A178505847748990053",
    "twid=u%3D2081335439026421760",
    "_twitter_sess=BAh7BiIKZmxhc2hJQzonQWN0aW9uQ29udHJvbGxlcjo6Rmxhc2g6OkZsYXNo%250ASGFzaHsABjoKQHVzZWR7AA%253D%253D--1164b91ac812d853b877e93ddb612b7471bebc74",
    "auth_multi=\"497862683:443bd09a5c16b0d8e346459f52686dc7be306564|1919756553915428864:a40bfcf10aa9fda18b4e1768fc6d63e567a9e5fc|1969781334114455552:3fe146efd1cc10b8179ef91e36f583d60a5c6e5b\"",
    "__cf_bm=gC8t1L9RsF3ndSQTlNW44GTP2fH6WB_86U2pvCjlV0U-1785063263.959605-1.0.1.1-D4toXEYknP5RJOyGlG4sM_HGw_2jhgUL6VTmOmum3utpnst26y3miE8TIaLHHRcRuu3qv8JqEVPNwzCXxdysjZc5qHIsdtkUpC0.rWlSzPWSCfviWn93gZVSUwcOiu3D",
    "ct0=bb33543802aefbd7f6b2496ef8ec78ec578d22decbc0b5a0fa2ff1d66846a7a57deff1cc2b0fbc16f7e3edb3b2bcb9b0758b128c9af16bf0133c44980671ba5f329812ffb971fdd03443edf83423e4ee",
    "kdt=I26qcLfGtmQPKocgpIA1CmOPLRiS2kYQu8CY2vdA",
    "personalization_id=\"v1_VF7XpjNa6DEkBMUivBb/xQ==\"",
])

USER_ID = '2081335439026421760'


def extract_query_id_from_page():
    """从页面 HTML 中提取 GraphQL query ID"""
    print('从页面提取 GraphQL query ID...')
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            viewport={'width': 1920, 'height': 1080}
        )
        
        for c in [
            {"domain": ".x.com", "name": "auth_token", "value": "0555da63fcf228b97af5aec8c8ed4fd6d5841880", "path": "/"},
            {"domain": ".x.com", "name": "guest_id", "value": "v1%3A178505847748990053", "path": "/"},
            {"domain": ".x.com", "name": "twid", "value": "u%3D2081335439026421760", "path": "/"},
            {"domain": ".x.com", "name": "_twitter_sess", "value": "BAh7BiIKZmxhc2hJQzonQWN0aW9uQ29udHJvbGxlcjo6Rmxhc2g6OkZsYXNo%250ASGFzaHsABjoKQHVzZWR7AA%253D%253D--1164b91ac812d853b877e93ddb612b7471bebc74", "path": "/"},
            {"domain": ".x.com", "name": "auth_multi", "value": "\"497862683:443bd09a5c16b0d8e346459f52686dc7be306564|1919756553915428864:a40bfcf10aa9fda18b4e1768fc6d63e567a9e5fc|1969781334114455552:3fe146efd1cc10b8179ef91e36f583d60a5c6e5b\"", "path": "/"},
            {"domain": ".x.com", "name": "__cf_bm", "value": "gC8t1L9RsF3ndSQTlNW44GTP2fH6WB_86U2pvCjlV0U-1785063263.959605-1.0.1.1-D4toXEYknP5RJOyGlG4sM_HGw_2jhgUL6VTmOmum3utpnst26y3miE8TIaLHHRcRuu3qv8JqEVPNwzCXxdysjZc5qHIsdtkUpC0.rWlSzPWSCfviWn93gZVSUwcOiu3D", "path": "/"},
            {"domain": ".x.com", "name": "ct0", "value": "bb33543802aefbd7f6b2496ef8ec78ec578d22decbc0b5a0fa2ff1d66846a7a57deff1cc2b0fbc16f7e3edb3b2bcb9b0758b128c9af16bf0133c44980671ba5f329812ffb971fdd03443edf83423e4ee", "path": "/"},
            {"domain": ".x.com", "name": "kdt", "value": "I26qcLfGtmQPKocgpIA1CmOPLRiS2kYQu8CY2vdA", "path": "/"},
            {"domain": ".x.com", "name": "personalization_id", "value": "\"v1_VF7XpjNa6DEkBMUivBb/xQ==\"", "path": "/"},
        ]:
            context.add_cookies([c])
        
        page = context.new_page()
        
        page.goto('https://x.com/tutu7gen1', wait_until='domcontentloaded', timeout=30000)
        time.sleep(5)
        
        html = page.content()
        
        # 搜索 GraphQL queryId
        query_ids = re.findall(r'queryId["\s]*[:=]["\s]*"([a-zA-Z0-9]{20,})"', html)
        print(f'找到 {len(query_ids)} 个 queryId')
        
        # 搜索特定的 query 名称
        if 'UserTweets' in html:
            user_tweets_match = re.search(r'"UserTweets"[^}]*"queryId"\s*:\s*"([a-zA-Z0-9]{20,})"', html)
            if user_tweets_match:
                print(f'UserTweets queryId: {user_tweets_match.group(1)}')
        
        # 搜索 Timeline 相关的 query
        timeline_matches = re.findall(r'"Timeline[^"]*Timeline[^"]*"', html)
        print(f'Timeline 相关 query: {timeline_matches[:5]}')
        
        browser.close()
        
        return query_ids


def fetch_with_dynamic_query():
    """使用动态获取的 query ID"""
    query_ids = extract_query_id_from_page()
    
    if not query_ids:
        print('未找到 queryId，尝试常用 query ID')
        # X 常见的 UserTweets query IDs (可能会变化)
        possible_ids = [
            'bJJiMoaPFmWPMI1a7cXEgT',  # UserTweetsAndRepliesByUserId
            'Jbggg0WF83MHTWXYCndXLw',  # UserTweets
            'QjMw4tXv3JfJqkOQo7VEcQ',  # UserTweetsAndReplies
            '2X7JGdI0aT5yOh7DPaGQtg',  # UserTimeline
        ]
        
        for qid in possible_ids:
            query_url = f'https://x.com/i/api/graphql/{qid}/UserTweetsAndRepliesByUserId'
            variables = {
                "userId": USER_ID,
                "count": 20,
                "includePromotedContent": False,
                "withVoice": False,
            }
            features = {
                "graphql_main_timelines_user_enabled": True,
            }
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
                'Authorization': 'Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGGrjMc',
                'Cookie': COOKIES_STR,
            }
            
            params = {
                'variables': json.dumps(variables),
                'features': json.dumps(features),
            }
            
            resp = requests.get(query_url, headers=headers, params=params, timeout=10)
            print(f'Query {qid}: Status {resp.status_code}')
            
            if resp.status_code == 200:
                print(f'成功！获取到数据')
                return resp.json()
    
    return None


def main():
    data = fetch_with_dynamic_query()
    
    if data:
        output = {
            'username': 'tutu7gen1',
            'scraped_at': datetime.now().isoformat(),
            'source': 'graphql_dynamic',
            'user_id': USER_ID,
            'raw_response': data,
        }
        
        output_path = f'{DATA_DIR}/tutu7gen1_tweets_dynamic_graphql.json'
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        
        print(f'\n数据已保存到 {output_path}')
    else:
        print('获取失败')


if __name__ == '__main__':
    main()
