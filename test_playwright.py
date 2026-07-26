from playwright.sync_api import sync_playwright
import json

def test():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        try:
            page.goto('https://syndication.twitter.com/srv/timeline-profile/screen-name/kaixintangtang', timeout=30000)
            page.wait_for_load_state('networkidle')
            print("Status:", page.title())
            content = page.content()
            print("Length:", len(content))
            with open('syndication.html', 'w', encoding='utf-8') as f:
                f.write(content)
        except Exception as e:
            print("Error:", e)
        finally:
            browser.close()

if __name__ == '__main__':
    test()
