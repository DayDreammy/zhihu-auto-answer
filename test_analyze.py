#!/usr/bin/env python3
"""
知乎页面分析测试 - 无头浏览器版本
用于获取知乎页面的实际HTML结构
"""
import asyncio
import json
from pathlib import Path

from playwright.async_api import async_playwright


async def analyze_zhihu_structure():
    """分析知乎页面结构"""
    
    async with async_playwright() as p:
        # 启动浏览器（有界面便于调试）
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        )
        page = await context.new_page()
        
        results = {
            'notifications_page': {},
            'login_status': False,
            'timestamp': str(asyncio.get_event_loop().time())
        }
        
        print("=" * 60)
        print("知乎页面结构分析")
        print("=" * 60)
        
        # 1. 访问知乎首页检查登录状态
        print("\n1. 访问知乎首页...")
        await page.goto("https://www.zhihu.com", wait_until='networkidle')
        await page.wait_for_timeout(3000)
        
        # 保存首页HTML
        home_html = await page.content()
        Path('debug_home.html').write_text(home_html, encoding='utf-8')
        print("   ✅ 首页HTML已保存到 debug_home.html")
        
        # 检查登录状态
        login_check = await page.evaluate('''() => {
            const indicators = [
                document.querySelector('.AppHeader-profileEntryAvatar'),
                document.querySelector('[data-za-detail-view-element_name="个人头像"]'),
                document.querySelector('img[alt*="头像"]'),
                document.querySelector('.AppHeader-userInfo')
            ];
            return indicators.some(el => el !== null);
        }''')
        
        results['login_status'] = login_check
        if login_check:
            print("   ✅ 检测到已登录")
        else:
            print("   ❌ 未登录（需要扫码登录）")
            print("\n   请在本地运行: python main.py --login")
        
        # 2. 访问通知页面
        print("\n2. 访问通知页面...")
        await page.goto("https://www.zhihu.com/notifications", wait_until='networkidle')
        await page.wait_for_timeout(5000)
        
        # 保存通知页面HTML
        notif_html = await page.content()
        Path('debug_notifications.html').write_text(notif_html, encoding='utf-8')
        print("   ✅ 通知页HTML已保存到 debug_notifications.html")
        
        # 分析通知列表
        notification_analysis = await page.evaluate('''() => {
            const results = {
                selectors_tested: [],
                items_found: 0,
                sample_items: []
            };
            
            const selectors = [
                '.NotificationList-item',
                '[class*="NotificationList"] > div',
                '.List-item',
                '.ContentItem',
                'div[role="listitem"]'
            ];
            
            for (const selector of selectors) {
                try {
                    const elements = document.querySelectorAll(selector);
                    results.selectors_tested.push({
                        selector: selector,
                        count: elements.length
                    });
                    
                    if (elements.length > 0 && results.items_found === 0) {
                        results.items_found = elements.length;
                        // 获取前3个样本
                        for (let i = 0; i < Math.min(3, elements.length); i++) {
                            const el = elements[i];
                            const text = el.textContent || '';
                            const hasInvitation = ['邀请你回答', '邀请回答', '向你提问'].some(kw => text.includes(kw));
                            
                            // 查找链接
                            const link = el.querySelector('a[href*="/question/"]');
                            
                            results.sample_items.push({
                                index: i,
                                text_preview: text.substring(0, 200),
                                has_invitation: hasInvitation,
                                link_found: link !== null,
                                link_href: link ? link.getAttribute('href') : null
                            });
                        }
                    }
                } catch (e) {
                    results.selectors_tested.push({
                        selector: selector,
                        error: e.message
                    });
                }
            }
            
            return results;
        }''')
        
        results['notifications_page'] = notification_analysis
        
        print("\n3. 分析结果:")
        print(f"   测试选择器数量: {len(notification_analysis['selectors_tested'])}")
        print(f"   找到通知项: {notification_analysis['items_found']}")
        
        if notification_analysis['sample_items']:
            print("\n   样本通知项:")
            for item in notification_analysis['sample_items']:
                print(f"\n   [{item['index']}] {'✅' if item['has_invitation'] else '❌'} 邀请相关")
                print(f"      链接: {item['link_found'] and '找到' or '未找到'} {item['link_href'] or ''}")
                print(f"      内容: {item['text_preview'][:100]}...")
        
        # 3. 如果找到邀请，访问问题页面分析编辑器
        invitation_items = [i for i in notification_analysis['sample_items'] if i['has_invitation']]
        if invitation_items and invitation_items[0]['link_href']:
            question_url = invitation_items[0]['link_href']
            if question_url.startswith('/'):
                question_url = f"https://www.zhihu.com{question_url}"
            
            print(f"\n4. 访问问题页面分析编辑器: {question_url[:60]}...")
            await page.goto(question_url, wait_until='networkidle')
            await page.wait_for_timeout(3000)
            
            # 保存问题页面
            question_html = await page.content()
            Path('debug_question.html').write_text(question_html, encoding='utf-8')
            
            # 分析编辑器
            editor_analysis = await page.evaluate('''() => {
                const results = {
                    write_button_found: false,
                    write_button_selectors: [],
                    editor_found: false,
                    editor_selectors: []
                };
                
                // 检查写回答按钮
                const writeSelectors = [
                    'button:has-text("写回答")',
                    'button:has-text("添加回答")',
                    '[data-za-detail-view-element_name="写回答"]',
                    'a[href*="/write"]'
                ];
                
                for (const selector of writeSelectors) {
                    try {
                        const btn = document.querySelector(selector);
                        if (btn) {
                            results.write_button_found = true;
                            results.write_button_selectors.push(selector);
                        }
                    } catch (e) {}
                }
                
                // 尝试点击写回答按钮看是否能找到编辑器
                const firstBtn = document.querySelector('button:has-text("写回答"), button:has-text("添加回答")');
                if (firstBtn) {
                    firstBtn.click();
                }
                
                return results;
            }''')
            
            results['question_page'] = editor_analysis
            print(f"   写回答按钮: {'✅' if editor_analysis['write_button_found'] else '❌'}")
        
        # 保存分析结果
        Path('analysis_result.json').write_text(
            json.dumps(results, indent=2, ensure_ascii=False),
            encoding='utf-8'
        )
        
        print("\n" + "=" * 60)
        print("分析完成!")
        print("=" * 60)
        print("\n输出文件:")
        print("  - debug_home.html: 知乎首页HTML")
        print("  - debug_notifications.html: 通知页HTML")
        print("  - debug_question.html: 问题页HTML")
        print("  - analysis_result.json: 结构化分析结果")
        
        await browser.close()
        return results


if __name__ == '__main__':
    results = asyncio.run(analyze_zhihu_structure())
    
    # 根据结果生成建议
    print("\n📋 建议:")
    if not results['login_status']:
        print("  1. 需要先登录知乎，运行: python main.py --login")
    elif results['notifications_page']['items_found'] == 0:
        print("  1. 通知列表为空或选择器需要调整")
        print("  2. 请检查 debug_notifications.html 查看实际结构")
    else:
        print("  1. 页面结构分析成功")
        print("  2. 可以运行主程序: python main.py")
