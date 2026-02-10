#!/usr/bin/env python3
"""
知乎页面结构分析工具
用于分析知乎的 DOM 结构，找到正确的选择器
"""
import asyncio
from playwright.async_api import async_playwright


async def analyze_zhihu():
    """分析知乎页面结构"""
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080}
        )
        page = await context.new_page()
        
        print("=" * 60)
        print("知乎页面结构分析工具")
        print("=" * 60)
        
        # 1. 分析通知页面
        print("\n📋 步骤1: 访问通知页面")
        print("URL: https://www.zhihu.com/notifications")
        await page.goto("https://www.zhihu.com/notifications")
        
        input("\n请登录知乎（如果未登录），然后按回车继续...")
        
        print("\n正在分析通知列表...")
        
        # 尝试不同的选择器
        selectors = [
            '.NotificationList-item',
            '[class*="Notification"]',
            '[class*="notification"]',
            '.List-item',
            '.ContentItem',
        ]
        
        for selector in selectors:
            elements = await page.query_selector_all(selector)
            print(f"  选择器 '{selector}': 找到 {len(elements)} 个元素")
        
        # 保存页面 HTML 用于分析
        html = await page.content()
        with open('notifications_page.html', 'w', encoding='utf-8') as f:
            f.write(html)
        print("\n💾 页面 HTML 已保存到 notifications_page.html")
        
        # 2. 分析问题页面
        print("\n📋 步骤2: 访问问题页面")
        question_url = input("请输入一个知乎问题链接（或按回车跳过）: ").strip()
        
        if question_url:
            await page.goto(question_url)
            await page.wait_for_timeout(3000)
            
            print("\n正在分析问题页面...")
            
            # 检查"写回答"按钮
            write_selectors = [
                'button:has-text("写回答")',
                'button:has-text("回答")',
                '[data-za-detail-view-element_name="回答"]',
                '.AnswerForm-editor',
            ]
            
            for selector in write_selectors:
                elem = await page.query_selector(selector)
                if elem:
                    print(f"  ✅ 找到: {selector}")
                else:
                    print(f"  ❌ 未找到: {selector}")
            
            # 检查编辑器
            editor_selectors = [
                '.RichText-editable',
                '[contenteditable="true"]',
                '.DraftEditor-root',
                '[class*="editor"]',
            ]
            
            print("\n编辑器选择器测试:")
            for selector in editor_selectors:
                elem = await page.query_selector(selector)
                if elem:
                    print(f"  ✅ 找到: {selector}")
                else:
                    print(f"  ❌ 未找到: {selector}")
        
        print("\n" + "=" * 60)
        print("分析完成！")
        print("=" * 60)
        
        await browser.close()


if __name__ == '__main__':
    asyncio.run(analyze_zhihu())
