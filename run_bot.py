#!/usr/bin/env python3
"""
知乎自动回答机器人 - 完整运行脚本
包含：扫码登录 -> 获取邀请 -> 生成回答 -> 保存草稿
"""
import asyncio
import json
import sys
from pathlib import Path

from playwright.async_api import async_playwright


class ZhihuBot:
    def __init__(self):
        self.cookie_file = Path('zhihu_cookies.json')
        self.browser = None
        self.context = None
        self.page = None
        
    async def init(self, headless=True):
        """初始化浏览器"""
        p = await async_playwright().start()
        self.browser = await p.chromium.launch(headless=headless)
        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080}
        )
        self.page = await self.context.new_page()
        
        # 加载已有cookie
        if self.cookie_file.exists():
            cookies = json.loads(self.cookie_file.read_text())
            await self.context.add_cookies(cookies)
            print(f"✅ 已加载 {len(cookies)} 个cookie")
    
    async def login(self):
        """扫码登录"""
        print('\\n' + '='*60)
        print('知乎登录')
        print('='*60)
        
        await self.page.goto('https://www.zhihu.com/signin')
        await self.page.wait_for_timeout(2000)
        
        # 切换到扫码登录
        qr_tab = await self.page.query_selector('[data-za-detail-view-element_name=\"扫码登录\"]')
        if qr_tab:
            await qr_tab.click()
            await self.page.wait_for_timeout(2000)
        
        # 等待二维码
        await self.page.wait_for_selector('canvas', timeout=10000)
        
        # 保存二维码截图
        await self.page.screenshot(path='qrcode.png')
        print('\\n📱 请查看 qrcode.png 文件，用知乎App扫码')
        print('   二维码有效期约2分钟...')
        
        # 等待登录成功
        try:
            await self.page.wait_for_selector('.AppHeader-profileEntryAvatar', timeout=120000)
            print('✅ 登录成功！')
            
            # 保存cookie
            cookies = await self.context.cookies()
            self.cookie_file.write_text(json.dumps(cookies, indent=2))
            print(f'✅ Cookie已保存到 {self.cookie_file}')
            return True
        except:
            print('❌ 登录超时')
            return False
    
    async def check_login(self):
        """检查登录状态"""
        await self.page.goto('https://www.zhihu.com', wait_until='networkidle')
        await self.page.wait_for_timeout(3000)
        
        avatar = await self.page.query_selector('.AppHeader-profileEntryAvatar')
        return avatar is not None
    
    async def get_invitations(self):
        """获取邀请列表（通过API）"""
        print('\\n🔍 正在获取邀请列表...')
        
        # 使用页面JS调用API
        result = await self.page.evaluate('''async () => {
            try {
                const response = await fetch('https://www.zhihu.com/api/v4/me/invitations?limit=20', {
                    headers: {
                        'Accept': 'application/json',
                        'X-Requested-With': 'fetch'
                    },
                    credentials: 'include'
                });
                
                if (!response.ok) {
                    return { error: 'API返回 ' + response.status };
                }
                
                const data = await response.json();
                return { success: true, data: data };
            } catch (e) {
                return { error: e.message };
            }
        }''')
        
        if 'error' in result:
            error_msg = result['error']
            print(f'❌ 获取邀请失败: {error_msg}')
            return []
        
        data = result.get('data', {})
        items = data.get('data', [])
        
        invitations = []
        for item in items:
            question = item.get('question', {})
            inv = {
                'id': str(question.get('id', '')),
                'title': question.get('title', ''),
                'url': f"https://www.zhihu.com/question/{question.get('id', '')}",
                'content': question.get('detail', '')[:500]
            }
            invitations.append(inv)
        
        print(f'✅ 找到 {len(invitations)} 个邀请')
        return invitations
    
    async def save_answer_to_draft(self, question_id, answer_text):
        """保存回答到草稿箱"""
        print(f'\\n💾 正在保存回答到草稿箱...')
        
        # 访问写回答页面
        url = f'https://www.zhihu.com/question/{question_id}/write'
        await self.page.goto(url, wait_until='networkidle')
        await self.page.wait_for_timeout(5000)
        
        # 查找编辑器
        editor_selectors = [
            '.RichText-editable',
            '[contenteditable=\"true\"]',
            'div[role=\"textbox\"]'
        ]
        
        editor = None
        for selector in editor_selectors:
            try:
                editor = await self.page.wait_for_selector(selector, timeout=5000)
                if editor:
                    print(f'  ✅ 找到编辑器')
                    break
            except:
                continue
        
        if not editor:
            print('  ❌ 未找到编辑器')
            return False
        
        # 输入回答
        await editor.click()
        await self.page.wait_for_timeout(500)
        
        # 清空并输入
        await self.page.keyboard.press('Control+a')
        await self.page.wait_for_timeout(200)
        await self.page.keyboard.press('Delete')
        await self.page.wait_for_timeout(200)
        
        await editor.fill(answer_text)
        await self.page.wait_for_timeout(3000)
        
        # 等待自动保存
        print('  ⏳ 等待自动保存...')
        await self.page.wait_for_timeout(5000)
        
        print('  ✅ 已保存到草稿箱')
        return True
    
    async def close(self):
        """关闭浏览器"""
        if self.browser:
            await self.browser.close()


async def main():
    print('='*60)
    print('知乎自动回答机器人')
    print('='*60)
    
    bot = ZhihuBot()
    
    try:
        # 初始化
        await bot.init(headless=True)
        
        # 检查登录
        print('\\n检查登录状态...')
        if not await bot.check_login():
            print('❌ 未登录，需要扫码')
            if not await bot.login():
                print('登录失败，退出')
                return
        
        # 获取邀请
        invitations = await bot.get_invitations()
        
        if not invitations:
            print('\\n📭 没有新的邀请')
            return
        
        print(f'\\n📋 发现 {len(invitations)} 个邀请:')
        for i, inv in enumerate(invitations, 1):
            title = inv['title'][:60]
            print(f'  {i}. {title}...')
        
        # 处理每个邀请
        for inv in invitations:
            print(f'\\n处理: {title}...')
            
            # 这里可以调用你的回答生成工具
            # 现在使用占位符
            answer = f"这是关于「{inv['title']}」的测试回答。\\n\\n请在 config.yaml 中配置实际回答生成工具。"
            
            # 保存到草稿
            success = await bot.save_answer_to_draft(inv['id'], answer)
            
            if success:
                print('✅ 完成')
            else:
                print('❌ 失败')
            
            await asyncio.sleep(3)
        
        print('\\n' + '='*60)
        print('处理完成')
        print('='*60)
        
    except KeyboardInterrupt:
        print('\\n\\n用户中断')
    except Exception as e:
        print(f'\\n❌ 错误: {e}')
        import traceback
        traceback.print_exc()
    finally:
        await bot.close()


if __name__ == '__main__':
    asyncio.run(main())
