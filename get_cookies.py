#!/usr/bin/env python3
"""
直接获取知乎Cookie（已有登录会话）
"""
import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright


async def get_zhihu_cookies():
    """获取已登录的知乎Cookie"""
    print("正在获取知乎Cookie...")
    
    async with async_playwright() as p:
        # 启动浏览器
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        )
        page = await context.new_page()
        
        # 访问知乎
        print("访问知乎...")
        await page.goto('https://www.zhihu.com', wait_until='networkidle')
        await page.wait_for_timeout(3000)
        
        # 检查是否已登录
        avatar = await page.query_selector('.AppHeader-profileEntryAvatar')
        if avatar:
            print("✅ 检测到已登录")
            
            # 保存Cookie
            cookies = await context.cookies()
            cookie_file = Path('zhihu_cookies.json')
            cookie_file.write_text(json.dumps(cookies, indent=2))
            print(f"✅ Cookie已保存到 {cookie_file}")
            print(f"   共 {len(cookies)} 个Cookie")
            
            # 显示关键Cookie
            for cookie in cookies:
                if cookie['name'] in ['z_c0', '_xsrf', 'd_c0']:
                    print(f"   - {cookie['name']}: {cookie['value'][:30]}...")
            
            await browser.close()
            return True
        else:
            print("❌ 未登录，需要重新扫码")
            await browser.close()
            return False


if __name__ == '__main__':
    result = asyncio.run(get_zhihu_cookies())
    if result:
        print("\n✅ Cookie获取成功，可以运行主程序了")
    else:
        print("\n❌ 需要先登录")
