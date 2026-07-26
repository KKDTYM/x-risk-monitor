const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
  });
  
  // 加载 cookies
  const cookiesPath = path.resolve(__dirname, 'conny_cookies.json');
  if (fs.existsSync(cookiesPath)) {
    console.log('Loading cookies from conny_cookies.json...');
    const cookies = JSON.parse(fs.readFileSync(cookiesPath, 'utf8'));
    // 转换或过滤 sameSite 属性
    const validCookies = cookies.map(c => {
      const copy = { ...c };
      // Playwright uses Strict, Lax, None (case sensitive) or omits it
      if (typeof copy.sameSite === 'string') {
        const lower = copy.sameSite.toLowerCase();
        if (lower === 'no_restriction') {
          copy.sameSite = 'None';
        } else if (lower === 'lax') {
          copy.sameSite = 'Lax';
        } else if (lower === 'strict') {
          copy.sameSite = 'Strict';
        } else {
          delete copy.sameSite;
        }
      } else {
        delete copy.sameSite;
      }
      return copy;
    });
    await context.addCookies(validCookies);
  } else {
    console.error('Error: conny_cookies.json not found!');
    process.exit(1);
  }

  const page = await context.newPage();
  
  console.log('Navigating to https://x.com/sino11680908...');
  await page.goto('https://x.com/sino11680908', { waitUntil: 'domcontentloaded', timeout: 60000 });
  
  console.log('Waiting for 15 seconds to allow AJAX resources to fully load...');
  await page.waitForTimeout(15000);
  
  const content = await page.content();
  const outputPath = path.resolve(__dirname, 'data/sino_debug.html');
  fs.writeFileSync(outputPath, content, 'utf8');
  console.log(`Successfully saved page content to ${outputPath}`);
  
  await browser.close();
})();
