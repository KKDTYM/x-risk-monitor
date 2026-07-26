import json
import os

for u in ['kaixintangtang', 'dangao0709', 'KkdTym']:
    print('='*60)
    print(f'账号 @{u} 获取到的推文列表 （当前共 {u} 篇）:')
    print('='*60)
    path = f'data/account_data/{u}/2026-07-24.json'
    if not os.path.exists(path):
        print(f"配置文件/历史记录不存在: {path}")
        continue
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            tweets = data.get('recent_tweets', [])
            if not tweets:
                print("暂无推文内容")
            for i, t in enumerate(tweets):
                tag = '[转发]' if t.get('is_retweet') else '[原创]'
                author = t.get('original_author', '')
                author_str = f' (作者: @{author})' if author and author != u else ''
                print(f'{i+1}. {tag}{author_str}: {t.get("text")}')
                print(f'   链接: {t.get("url")}')
                print(f'   可能敏感(possibly_sensitive): {t.get("possibly_sensitive")}')
                print(f'   发布时间: {t.get("created_at")}')
                print('-'*40)
    except Exception as e:
        print(f'读取账号 @{u} 数据失败: {e}')
