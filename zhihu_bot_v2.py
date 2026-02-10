#!/usr/bin/env python3
"""
知乎自动回答机器人 - 生产就绪版本
支持Cookie登录，直接调用知乎API
"""
import asyncio
import json
import re
import subprocess
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

import requests
from playwright.async_api import async_playwright, Page, Browser, BrowserContext


@dataclass
class Question:
    id: str
    title: str
    url: str
    content: str = ""


@dataclass
class Invitation:
    question: Question
    inviter: Optional[str] = None


class ZhihuAutoAnswer:
    """知乎自动回答机器人"""
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Referer': 'https://www.zhihu.com/',
            'X-Requested-With': 'fetch',
        })
        
        self.cookie_file = Path("zhihu_cookies.json")
        self.processed_file = Path("processed_invitations.json")
        self.processed_ids = self._load_processed_ids()
        
        # Playwright相关
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
    
    def _load_processed_ids(self) -> set:
        """加载已处理的邀请ID"""
        if self.processed_file.exists():
            try:
                data = json.loads(self.processed_file.read_text())
                return set(data.get('processed_ids', []))
            except:
                pass
        return set()
    
    def _save_processed_ids(self):
        """保存已处理的邀请ID"""
        self.processed_file.write_text(json.dumps({
            'processed_ids': list(self.processed_ids),
            'updated_at': datetime.now().isoformat()
        }, indent=2, ensure_ascii=False))
    
    def load_cookies_from_file(self, cookie_file: Optional[str] = None) -> bool:
        """从文件加载Cookie"""
        file_path = Path(cookie_file) if cookie_file else self.cookie_file
        
        if not file_path.exists():
            print(f"❌ Cookie文件不存在: {file_path}")
            return False
        
        try:
            cookies = json.loads(file_path.read_text())
            
            # 支持两种格式：Playwright格式和普通格式
            for cookie in cookies:
                if 'name' in cookie and 'value' in cookie:
                    # Playwright格式
                    self.session.cookies.set(
                        cookie['name'],
                        cookie['value'],
                        domain=cookie.get('domain', '.zhihu.com'),
                        path=cookie.get('path', '/')
                    )
                elif len(cookie) >= 2:
                    # 简单格式 [name, value]
                    self.session.cookies.set(cookie[0], cookie[1])
            
            print(f"✅ 已加载 {len(cookies)} 个Cookie")
            return True
        except Exception as e:
            print(f"❌ 加载Cookie失败: {e}")
            return False
    
    def load_cookies_from_string(self, cookie_string: str):
        """从字符串加载Cookie (格式: name1=value1; name2=value2)"""
        try:
            for item in cookie_string.split(';'):
                item = item.strip()
                if '=' in item:
                    name, value = item.split('=', 1)
                    self.session.cookies.set(name.strip(), value.strip())
            print(f"✅ 已从字符串加载Cookie")
            return True
        except Exception as e:
            print(f"❌ 解析Cookie失败: {e}")
            return False
    
    def save_cookies_to_file(self, cookie_file: Optional[str] = None):
        """保存Cookie到文件"""
        file_path = Path(cookie_file) if cookie_file else self.cookie_file
        
        cookies = []
        for name, value in self.session.cookies.items():
            cookies.append({
                'name': name,
                'value': value,
                'domain': '.zhihu.com',
                'path': '/'
            })
        
        file_path.write_text(json.dumps(cookies, indent=2))
        print(f"✅ Cookie已保存到 {file_path}")
    
    def check_login(self) -> bool:
        """检查是否已登录"""
        try:
            response = self.session.get(
                'https://www.zhihu.com/api/v4/me',
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ 已登录: {data.get('name', '未知用户')}")
                return True
            else:
                print(f"❌ 未登录 (状态码: {response.status_code})")
                return False
        except Exception as e:
            print(f"❌ 检查登录失败: {e}")
            return False
    
    def get_invitations(self) -> List[Invitation]:
        """获取邀请回答列表"""
        print("🔍 正在获取邀请列表...")
        invitations = []
        
        try:
            # API端点
            url = 'https://www.zhihu.com/api/v4/me/invitations'
            
            params = {
                'limit': 20,
                'offset': 0,
            }
            
            response = self.session.get(url, params=params, timeout=10)
            
            if response.status_code != 200:
                print(f"❌ 获取邀请失败: {response.status_code}")
                print(f"   响应: {response.text[:200]}")
                return invitations
            
            data = response.json()
            
            # 解析数据
            if isinstance(data, dict):
                items = data.get('data', [])
                
                print(f"📊 获取到 {len(items)} 个邀请")
                
                for item in items:
                    try:
                        # 提取问题信息
                        question_data = item.get('question', {})
                        if not question_data:
                            continue
                        
                        question_id = str(question_data.get('id', ''))
                        title = question_data.get('title', '')
                        
                        if not question_id or not title:
                            continue
                        
                        # 检查是否已处理
                        if question_id in self.processed_ids:
                            print(f"  ⏭️  跳过已处理: {title[:50]}...")
                            continue
                        
                        question = Question(
                            id=question_id,
                            title=title,
                            url=f"https://www.zhihu.com/question/{question_id}",
                            content=question_data.get('detail', '')[:1000]
                        )
                        
                        invitation = Invitation(
                            question=question,
                            inviter=item.get('sender', {}).get('name')
                        )
                        
                        invitations.append(invitation)
                        print(f"  📌 新邀请: {title[:60]}...")
                        
                    except Exception as e:
                        print(f"  ⚠️ 解析邀请失败: {e}")
            
        except Exception as e:
            print(f"❌ 获取邀请失败: {e}")
        
        return invitations
    
    def generate_answer(self, question: Question) -> str:
        """调用外部工具生成回答"""
        command_template = self.config.get('answer_generator', {}).get('command', '')
        
        if not command_template or 'echo' in command_template:
            print("⚠️ 未配置回答生成工具，使用占位符")
            return f"关于「{question.title}」的回答（由AI生成）"
        
        command = command_template
        command = command.replace('{title}', f'"{question.title}"')
        command = command.replace('{content}', f'"{question.content[:500]}"')
        
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode != 0:
                print(f"❌ 生成回答失败: {result.stderr}")
                return ""
            
            answer = result.stdout.strip()
            print(f"✅ 回答生成完成，长度: {len(answer)}")
            return answer
            
        except Exception as e:
            print(f"❌ 生成回答失败: {e}")
            return ""
    
    async def init_browser(self, headless: bool = True):
        """初始化Playwright浏览器"""
        self.playwright = await async_playwright().start()
        
        self.browser = await self.playwright.chromium.launch(headless=headless)
        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        )
        
        # 加载Cookie到浏览器
        for name, value in self.session.cookies.items():
            await self.context.add_cookies([{
                'name': name,
                'value': value,
                'domain': '.zhihu.com',
                'path': '/'
            }])
        
        self.page = await self.context.new_page()
    
    async def save_answer_to_draft(self, question: Question, answer: str) -> bool:
        """保存回答到草稿箱（使用浏览器自动化）"""
        print(f"💾 正在保存到草稿箱: {question.title[:50]}...")
        
        try:
            # 访问写回答页面
            write_url = f"https://www.zhihu.com/question/{question.id}/write"
            await self.page.goto(write_url, wait_until='networkidle')
            await self.page.wait_for_timeout(5000)
            
            # 查找编辑器
            editor_selectors = [
                '.RichText-editable',
                '[contenteditable="true"]',
                'div[role="textbox"]',
            ]
            
            editor = None
            for selector in editor_selectors:
                try:
                    editor = await self.page.wait_for_selector(selector, timeout=5000)
                    if editor:
                        print(f"  ✅ 找到编辑器: {selector}")
                        break
                except:
                    continue
            
            if not editor:
                print("  ❌ 未找到编辑器")
                return False
            
            # 输入回答
            await editor.click()
            await self.page.wait_for_timeout(500)
            
            # 清空并输入
            await self.page.keyboard.press('Control+a')
            await self.page.wait_for_timeout(200)
            await self.page.keyboard.press('Delete')
            await self.page.wait_for_timeout(200)
            
            await editor.fill(answer)
            await self.page.wait_for_timeout(3000)
            
            # 等待自动保存
            print("  ⏳ 等待自动保存...")
            await self.page.wait_for_timeout(5000)
            
            print(f"  ✅ 回答已保存到草稿箱")
            return True
            
        except Exception as e:
            print(f"  ❌ 保存失败: {e}")
            return False
    
    async def close_browser(self):
        """关闭浏览器"""
        if self.browser:
            await self.browser.close()
        if hasattr(self, 'playwright'):
            await self.playwright.stop()
    
    def send_notification(self, message: str):
        """发送飞书通知"""
        webhook = self.config.get('notification', {}).get('feishu_webhook', '')
        if not webhook:
            return
        
        try:
            requests.post(webhook, json={
                "msg_type": "text",
                "content": {"text": message}
            }, timeout=10)
            print("✅ 通知已发送")
        except Exception as e:
            print(f"⚠️ 发送通知失败: {e}")
    
    async def run(self, headless: bool = True):
        """主运行流程"""
        print("=" * 60)
        print("知乎自动回答机器人")
        print("=" * 60)
        
        # 检查登录
        if not self.check_login():
            print("\n❌ 请先提供Cookie或登录")
            print("方法1: 运行 --login 扫码登录")
            print("方法2: 从浏览器导出Cookie到 zhihu_cookies.json")
            return
        
        # 获取邀请
        invitations = self.get_invitations()
        
        if not invitations:
            print("\n📭 没有新的邀请")
            return
        
        # 初始化浏览器
        print("\n🌐 启动浏览器...")
        await self.init_browser(headless=headless)
        
        processed = []
        failed = []
        
        try:
            for i, invitation in enumerate(invitations):
                print(f"\n[{i+1}/{len(invitations)}] 处理: {invitation.question.title[:50]}...")
                
                # 生成回答
                answer = self.generate_answer(invitation.question)
                if not answer:
                    failed.append(invitation.question.title)
                    continue
                
                # 保存到草稿
                success = await self.save_answer_to_draft(invitation.question, answer)
                
                if success:
                    processed.append(invitation.question)
                    self.processed_ids.add(invitation.question.id)
                    self._save_processed_ids()
                else:
                    failed.append(invitation.question.title)
                
                # 间隔
                if i < len(invitations) - 1:
                    await asyncio.sleep(5)
        
        finally:
            await self.close_browser()
        
        # 发送通知
        if processed or failed:
            message = f"🤖 知乎自动回答机器人\n\n"
            message += f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
            
            if processed:
                message += f"✅ 成功处理 {len(processed)} 个:\n"
                for q in processed:
                    message += f"\n📌 {q.title[:50]}...\n"
                    message += f"   {q.url}\n"
            
            if failed:
                message += f"\n❌ 失败 {len(failed)} 个\n"
            
            self.send_notification(message)
        
        print("\n" + "=" * 60)
        print(f"✅ 成功: {len(processed)} 个")
        print(f"❌ 失败: {len(failed)} 个")
        print("=" * 60)


async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='知乎自动回答机器人')
    parser.add_argument('--login', action='store_true', help='扫码登录')
    parser.add_argument('--cookie', help='从文件加载Cookie')
    parser.add_argument('--cookie-string', help='从字符串加载Cookie')
    parser.add_argument('--headless', action='store_true', default=True, help='无界面模式')
    parser.add_argument('--no-headless', dest='headless', action='store_false', help='有界面模式')
    
    args = parser.parse_args()
    
    # 加载配置
    config = {}
    config_file = Path('config.yaml')
    if config_file.exists():
        import yaml
        config = yaml.safe_load(config_file.read_text()) or {}
    
    bot = ZhihuAutoAnswer(config)
    
    # 加载Cookie
    if args.cookie:
        bot.load_cookies_from_file(args.cookie)
    elif args.cookie_string:
        bot.load_cookies_from_string(args.cookie_string)
    elif bot.cookie_file.exists():
        bot.load_cookies_from_file()
    
    if args.login:
        # 扫码登录模式
        print("启动扫码登录...")
        await bot.init_browser(headless=False)
        
        from playwright.async_api import async_playwright
        
        page = bot.page
        await page.goto("https://www.zhihu.com/signin")
        print("请扫描二维码登录...")
        
        try:
            await page.wait_for_selector('.AppHeader-profileEntryAvatar', timeout=120000)
            print("✅ 登录成功！")
            
            # 保存Cookie
            cookies = await bot.context.cookies()
            bot.cookie_file.write_text(json.dumps(cookies, indent=2))
            print(f"✅ Cookie已保存")
        except:
            print("❌ 登录超时")
        
        await bot.close_browser()
    else:
        # 正常运行
        await bot.run(headless=args.headless)


if __name__ == '__main__':
    asyncio.run(main())
