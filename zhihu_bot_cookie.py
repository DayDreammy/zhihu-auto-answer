#!/usr/bin/env python3
"""
使用已有Cookie直接运行知乎机器人
"""
import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright


class ZhihuBotWithCookie:
    def __init__(self, cookie_file='zhihu_cookies.json'):
        self.cookie_file = Path(cookie_file)
        self.browser = None
        self.context = None
        self.page = None
        
    async def init(self, headless=True):
        """初始化浏览器并加载Cookie"""
        p = await async_playwright().start()
        self.playwright = p
        
        # 启动参数 - 绕过反检测
        launch_args = {
            'headless': headless,
            'args': [
                '--disable-blink-features=AutomationControlled',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process',
            ]
        }
        
        self.browser = await p.chromium.launch(**launch_args)
        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            locale='zh-CN',
            timezone_id='Asia/Shanghai',
        )
        
        self.page = await self.context.new_page()
        
        # 加载Cookie
        if self.cookie_file.exists():
            cookies = json.loads(self.cookie_file.read_text())
            await self.context.add_cookies(cookies)
            print(f"✅ 已加载 {len(cookies)} 个Cookie")
            return True
        return False
    
    async def check_login(self):
        """检查登录状态"""
        await self.page.goto('https://www.zhihu.com', wait_until='networkidle')
        await self.page.wait_for_timeout(3000)
        
        avatar = await self.page.query_selector('.AppHeader-profileEntryAvatar')
        if avatar:
            print('✅ 已登录')
            return True
        return False
    
    async def get_invitations(self):
        """获取邀请列表"""
        print('\n🔍 正在获取邀请列表...')
        
        result = await self.page.evaluate('''async () => {
            try {
                const response = await fetch('https://www.zhihu.com/api/v4/me/invitations?limit=20', {
                    headers: { 'Accept': 'application/json', 'X-Requested-With': 'fetch' },
                    credentials: 'include'
                });
                
                if (!response.ok) return { error: 'API返回 ' + response.status };
                
                const data = await response.json();
                return { success: true, data: data };
            } catch (e) {
                return { error: e.message };
            }
        }''')
        
        if 'error' in result:
            print(f'❌ 获取失败: {result["error"]}')
            return []
        
        items = result.get('data', {}).get('data', [])
        invitations = []
        
        for item in items:
            try:
                question = item.get('question', {})
                invitations.append({
                    'id': str(question.get('id', '')),
                    'title': question.get('title', ''),
                    'url': f"https://www.zhihu.com/question/{question.get('id', '')}",
                    'content': question.get('detail', '')[:500]
                })
            except:
                pass
        
        print(f'✅ 找到 {len(invitations)} 个邀请')
        return invitations
    
    async def save_answer_to_draft(self, question_id, answer_text):
        """保存回答到草稿箱"""
        print(f'💾 保存回答...')
        
        url = f'https://www.zhihu.com/question/{question_id}/write'
        await self.page.goto(url, wait_until='networkidle')
        await self.page.wait_for_timeout(5000)
        
        # 查找编辑器
        editor = None
        for selector in ['.RichText-editable', '[contenteditable="true"]', 'div[role="textbox"]']:
            try:
                editor = await self.page.wait_for_selector(selector, timeout=5000)
                if editor:
                    break
            except:
                continue
        
        if not editor:
            print('  ❌ 未找到编辑器')
            return False
        
        # 输入回答
        await editor.click()
        await self.page.keyboard.press('Control+a')
        await self.page.keyboard.press('Delete')
        await editor.fill(answer_text)
        await self.page.wait_for_timeout(3000)
        
        # 等待自动保存
        print('  ⏳ 等待自动保存...')
        await self.page.wait_for_timeout(5000)
        
        print('  ✅ 已保存')
        return True
    
    async def close(self):
        if self.browser:
            await self.browser.close()
        if hasattr(self, 'playwright'):
            await self.playwright.stop()


async def main():
    print('='*60)
    print('知乎自动回答机器人 - Cookie模式')
    print('='*60)
    
    bot = ZhihuBotWithCookie()
    
    try:
        # 初始化并加载Cookie
        if not await bot.init(headless=True):
            print('\n❌ 没有找到Cookie文件')
            print('请从浏览器导出知乎Cookie并保存为 zhihu_cookies.json')
            return
        
        # 检查登录
        print('\n检查登录状态...')
        if not await bot.check_login():
            print('❌ Cookie已失效，需要重新登录')
            return
        
        # 获取邀请
        invitations = await bot.get_invitations()
        
        if not invitations:
            print('\n📭 没有新的邀请')
            return
        
        print(f'\n📋 发现 {len(invitations)} 个邀请:')
        for i, inv in enumerate(invitations, 1):
            print(f'  {i}. {inv["title"][:60]}...')
        
        # 处理邀请
        processed = 0
        for inv in invitations:
            print(f'\n处理: {inv["title"][:50]}...')
            
            # 生成回答（替换为你的工具）
            answer = f"关于「{inv['title']}」的回答:\n\n[替换为实际生成的回答]"
            
            if await bot.save_answer_to_draft(inv['id'], answer):
                print('✅ 完成')
                processed += 1
            else:
                print('❌ 失败')
            
            await asyncio.sleep(3)
        
        print(f'\n✅ 成功处理 {processed}/{len(invitations)} 个邀请')
        
    except Exception as e:
        print(f'\n❌ 错误: {e}')
        import traceback
        traceback.print_exc()
    finally:
        await bot.close()


if __name__ == '__main__':
    asyncio.run(main())
