#!/usr/bin/env python3
"""
知乎自动回答机器人 - 无头模式版本
支持：生成二维码图片 -> 发送通知 -> 等待扫码 -> 自动继续
"""
import asyncio
import json
import sys
import time
from pathlib import Path
from playwright.async_api import async_playwright

# Avoid UnicodeEncodeError on Windows consoles (cp936/gbk) when printing non-ASCII.
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


class ZhihuBot:
    def __init__(self):
        self.cookie_file = Path('zhihu_cookies.json')
        self.browser = None
        self.context = None
        self.page = None
        
    async def init(self, headless=True):
        """初始化浏览器（无头模式）"""
        p = await async_playwright().start()
        self.playwright = p
        
        # 启动参数 - 绕过反检测
        launch_args = {
            'headless': headless,
            'args': [
                '--disable-blink-features=AutomationControlled',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-setuid-sandbox',
            ]
        }
        
        self.browser = await p.chromium.launch(**launch_args)
        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='zh-CN',
            timezone_id='Asia/Shanghai',
        )
        
        self.page = await self.context.new_page()
        
        # 注入脚本隐藏自动化特征
        await self.page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
            window.chrome = { runtime: {} };
            Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN', 'zh', 'en']});
        """)
        
        # 加载已有cookie
        if self.cookie_file.exists():
            try:
                cookies = json.loads(self.cookie_file.read_text())
                await self.context.add_cookies(cookies)
                print(f"✅ 已加载 {len(cookies)} 个cookie")
                return True
            except Exception as e:
                print(f"⚠️ 加载cookie失败: {e}")
        return False
    
    async def login_with_qrcode(self):
        """扫码登录流程"""
        print('\n' + '='*60)
        print('知乎扫码登录')
        print('='*60)
        
        # 访问登录页
        await self.page.goto('https://www.zhihu.com/signin')
        await self.page.wait_for_timeout(2000)
        
        # 切换到扫码登录
        qr_tab = await self.page.query_selector('[data-za-detail-view-element_name="扫码登录"]')
        if qr_tab:
            await qr_tab.click()
            await self.page.wait_for_timeout(2000)
        
        # 等待二维码
        await self.page.wait_for_selector('canvas', timeout=10000)
        
        # 获取二维码元素并单独截图（更清晰）
        qr_canvas = await self.page.query_selector('canvas')
        if qr_canvas:
            # 获取二维码的位置和大小
            bbox = await qr_canvas.bounding_box()
            # 截图二维码区域（稍微扩大一点边距）
            await self.page.screenshot(
                path='qrcode.png',
                clip={
                    'x': bbox['x'] - 20,
                    'y': bbox['y'] - 20,
                    'width': bbox['width'] + 40,
                    'height': bbox['height'] + 40
                }
            )
            print('\n📱 二维码已生成: qrcode.png (仅二维码区域)')
        else:
            # 备用：截取整个登录区域
            await self.page.screenshot(path='qrcode.png')
            print('\n📱 二维码已生成: qrcode.png')
        
        # 这里可以添加发送二维码到飞书的代码
        await self.send_qrcode_notification()
        
        print('\n⏳ 等待扫码登录（2分钟）...')
        print('   请用知乎App扫描二维码')
        
        # 等待登录成功（不要仅依赖单一 selector；扫码成功后可能不会立即出现头像元素）
        try:
            if not await self._wait_for_login(timeout_ms=120000):
                raise TimeoutError("login wait timeout")

            print("✅ 登录成功！")
            await self._save_cookies()
            return True
            
        except Exception as e:
            # 检查是否是安全验证页面
            current_url = self.page.url
            if 'unhuman' in current_url or 'account' in current_url:
                print('\n⚠️ 检测到安全验证页面')
                print('   请在浏览器中完成安全验证')
                print('   等待30秒后继续...')
                await self.page.wait_for_timeout(30000)
                
                # 再次检查是否登录成功
                try:
                    await self.page.wait_for_selector('.AppHeader-profileEntryAvatar', timeout=10000)
                    print('✅ 登录成功！')
                    cookies = await self.context.cookies()
                    self.cookie_file.write_text(json.dumps(cookies, indent=2))
                    return True
                except:
                    pass
            
            print(f'❌ 登录超时: {e}')
            return False
    
    async def send_qrcode_notification(self):
        """发送二维码通知（可集成飞书）"""
        # 如果有飞书webhook，可以在这里发送图片
        # 暂时只是打印提示
        print('\n💡 提示：可以将 qrcode.png 发送到飞书或微信')
    
    async def check_login(self):
        """检查登录状态"""
        await self.page.goto('https://www.zhihu.com', wait_until='networkidle')
        await self.page.wait_for_timeout(3000)
        
        avatar = await self.page.query_selector('.AppHeader-profileEntryAvatar')
        if avatar:
            print('✅ 已登录')
            return True
        return False

    async def _save_cookies(self):
        cookies = await self.context.cookies()
        self.cookie_file.write_text(
            json.dumps(cookies, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        print("✅ Cookie已保存")

    async def _is_logged_in(self) -> bool:
        # 1) DOM 指示器
        try:
            if await self.page.query_selector(".AppHeader-profileEntryAvatar"):
                return True
        except Exception:
            pass

        # 2) Cookie（扫码成功后通常会先写入 z_c0）
        try:
            cookies = await self.context.cookies("https://www.zhihu.com")
            if any(c.get("name") == "z_c0" and c.get("value") for c in cookies):
                return True
        except Exception:
            pass

        # 3) API 校验（200 即认为登录成功）
        try:
            result = await self.page.evaluate(
                """async () => {
                    try {
                        const resp = await fetch('https://www.zhihu.com/api/v4/me', {
                            method: 'GET',
                            credentials: 'include',
                            headers: { 'Accept': 'application/json', 'X-Requested-With': 'fetch' }
                        });
                        return { ok: resp.ok, status: resp.status };
                    } catch (e) {
                        return { ok: false, error: String(e) };
                    }
                }"""
            )
            if isinstance(result, dict) and result.get("ok") and result.get("status") == 200:
                return True
        except Exception:
            pass

        return False

    async def _wait_for_login(self, timeout_ms: int) -> bool:
        start = time.monotonic()
        last_print = 0.0

        while (time.monotonic() - start) * 1000 < timeout_ms:
            if await self._is_logged_in():
                return True

            # 每 5 秒输出一次状态，避免看起来“无响应”
            if time.monotonic() - last_print > 5:
                elapsed = int(time.monotonic() - start)
                print(f"⏳ 仍在等待登录确认... 已等待 {elapsed}s")
                last_print = time.monotonic()

            await asyncio.sleep(1)

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
    print('知乎自动回答机器人 - 无头模式')
    print('='*60)
    
    bot = ZhihuBot()
    
    try:
        # 初始化（无头模式，不需要图形界面）
        has_cookie = await bot.init(headless=True)
        
        # 检查登录
        if has_cookie and await bot.check_login():
            print('✅ 使用已有Cookie登录')
        else:
            print('❌ 需要扫码登录')
            if not await bot.login_with_qrcode():
                print('登录失败')
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
            
            # TODO: 替换为你的回答生成工具
            answer = f"关于「{inv['title']}」的回答:\n\n[此处替换为实际生成的回答内容]"
            
            if await bot.save_answer_to_draft(inv['id'], answer):
                print('✅ 完成')
                processed += 1
            else:
                print('❌ 失败')
            
            await asyncio.sleep(3)
        
        print(f'\n✅ 成功处理 {processed}/{len(invitations)} 个邀请')
        
    except Exception as e:
        print(f'\n❌ 错误: {e}')
    finally:
        await bot.close()


if __name__ == '__main__':
    asyncio.run(main())
