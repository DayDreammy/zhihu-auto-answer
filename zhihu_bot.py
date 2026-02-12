#!/usr/bin/env python3
"""
知乎自动回答机器人 - 核心模块 v2
支持多种选择器配置，更好的错误处理
"""
import asyncio
import json
import re
import time
import logging
import subprocess
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

from playwright.async_api import async_playwright, Page, Browser, BrowserContext
import yaml

# 导入选择器配置
try:
    from zhihu_selectors import (
        NOTIFICATION_SELECTORS, INVITATION_KEYWORDS, QUESTION_LINK_SELECTORS,
        LOGIN_INDICATORS, WRITE_ANSWER_BUTTONS, EDITOR_SELECTORS,
        SAVE_DRAFT_BUTTONS, QUESTION_TITLE_SELECTORS, QUESTION_CONTENT_SELECTORS
    )
except ImportError:
    # 如果 selectors.py 不存在，使用默认配置
    NOTIFICATION_SELECTORS = ['.NotificationList-item', '.List-item']
    INVITATION_KEYWORDS = ['邀请你回答', '邀请回答']
    QUESTION_LINK_SELECTORS = ['a[href*="/question/"]']
    LOGIN_INDICATORS = ['.AppHeader-profileEntryAvatar']
    WRITE_ANSWER_BUTTONS = ['button:has-text("写回答")']
    EDITOR_SELECTORS = ['.RichText-editable', '[contenteditable="true"]']
    SAVE_DRAFT_BUTTONS = ['button:has-text("保存草稿")']
    QUESTION_TITLE_SELECTORS = ['h1.QuestionHeader-title']
    QUESTION_CONTENT_SELECTORS = ['.QuestionRichText']


LOG_DIR = Path("logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

# 配置日志（FileHandler 不会自动创建目录，因此必须提前 mkdir）
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / "zhihu_bot.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


@dataclass
class Question:
    """问题数据结构"""
    id: str
    title: str
    url: str
    content: str = ""
    
    def to_dict(self):
        return asdict(self)


@dataclass  
class Invitation:
    """邀请数据结构"""
    question: Question
    inviter: str = ""
    invited_at: str = ""


class ZhihuAutoAnswer:
    """知乎自动回答机器人"""
    
    def __init__(self, config_path: str = "config.yaml"):
        self.config = self._load_config(config_path)
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.use_persistent_profile = False
        self.user_data_dir: Optional[Path] = None
        self.cookie_file = Path("zhihu_cookies.json")
        self.processed_file = Path("processed_invitations.json")
        self.processed_ids = self._load_processed_ids()
        
    def _load_config(self, path: str) -> dict:
        """加载配置文件"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            return {}
    
    def _load_processed_ids(self) -> set:
        """加载已处理的邀请ID"""
        if self.processed_file.exists():
            try:
                data = json.loads(self.processed_file.read_text(encoding="utf-8"))
                return set(data.get('processed_ids', []))
            except:
                pass
        return set()
    
    def _save_processed_ids(self):
        """保存已处理的邀请ID"""
        try:
            self.processed_file.write_text(json.dumps({
                'processed_ids': list(self.processed_ids),
                'updated_at': datetime.now().isoformat()
            }, indent=2, ensure_ascii=False))
        except Exception as e:
            logger.error(f"保存处理记录失败: {e}")
    
    async def init_browser(self, headless: bool = False, user_data_dir: Optional[str] = None):
        """初始化浏览器"""
        logger.info("正在初始化浏览器...")
        self.playwright = await async_playwright().start()
        
        launch_args = {
            'headless': headless,
            'args': [
                '--disable-blink-features=AutomationControlled',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process',
            ]
        }
        context_args = {
            'viewport': {'width': 1920, 'height': 1080},
            'user_agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'locale': 'zh-CN',
            'timezone_id': 'Asia/Shanghai',
        }

        if user_data_dir:
            self.use_persistent_profile = True
            self.user_data_dir = Path(user_data_dir)
            self.user_data_dir.mkdir(parents=True, exist_ok=True)
            self.context = await self.playwright.chromium.launch_persistent_context(
                user_data_dir=str(self.user_data_dir),
                **launch_args,
                **context_args,
            )
            self.browser = None
            logger.info(f"使用持久化用户目录: {self.user_data_dir.resolve()}")
        else:
            self.use_persistent_profile = False
            self.user_data_dir = None
            self.browser = await self.playwright.chromium.launch(**launch_args)
            self.context = await self.browser.new_context(**context_args)
            
            # 非持久化模式下，尝试加载 Cookie 文件
            if self.cookie_file.exists():
                try:
                    cookies = json.loads(self.cookie_file.read_text(encoding="utf-8"))
                    await self.context.add_cookies(cookies)
                    logger.info(f"已加载 {len(cookies)} 个 Cookie")
                except Exception as e:
                    logger.warning(f"加载 Cookie 失败: {e}")

        # 持久化上下文可能已有页面，优先复用
        pages = self.context.pages
        self.page = pages[0] if pages else await self.context.new_page()

        # 隐藏自动化特征
        await self.context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
            window.chrome = { runtime: {} };
        """)
        
        logger.info("浏览器初始化完成")
    
    async def save_cookies(self):
        """保存 Cookie"""
        try:
            cookies = await self.context.cookies()
            self.cookie_file.write_text(
                json.dumps(cookies, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            if self.use_persistent_profile and self.user_data_dir:
                logger.info(f"Cookie 已保存（持久化目录模式 + 备份文件 {self.cookie_file}）")
            else:
                logger.info("Cookie 已保存")
        except Exception as e:
            logger.error(f"保存 Cookie 失败: {e}")

    async def _is_logged_in(self) -> bool:
        """更稳健的登录判定：DOM 指示器 + API 校验（避免仅依赖单一 selector）。"""
        if not self.page:
            return False

        # 1) DOM 指示器
        for selector in LOGIN_INDICATORS:
            try:
                if await self.page.query_selector(selector):
                    return True
            except Exception:
                continue

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

    async def _wait_for_login(self, timeout_ms: int = 180000) -> bool:
        """等待登录完成，并定期输出进度，避免“看起来卡住”。"""
        start = time.monotonic()
        last_log = 0.0

        while (time.monotonic() - start) * 1000 < timeout_ms:
            # 安全验证页提示
            try:
                url = self.page.url or ""
                if "unhuman" in url or "/account" in url:
                    if time.monotonic() - last_log > 5:
                        logger.warning("检测到安全验证/风控页面，请在打开的浏览器窗口完成验证后等待程序继续...")
                        last_log = time.monotonic()
            except Exception:
                pass

            if await self._is_logged_in():
                return True

            # 每 5 秒打一条进度，避免用户以为无响应
            if time.monotonic() - last_log > 5:
                elapsed = int(time.monotonic() - start)
                logger.info(f"等待扫码确认中... 已等待 {elapsed}s")
                last_log = time.monotonic()

            await asyncio.sleep(1)

        return False
    
    async def check_login(self) -> bool:
        """检查是否已登录"""
        logger.info("检查登录状态...")
        try:
            await self.page.goto("https://www.zhihu.com", wait_until='networkidle')
            await self.page.wait_for_timeout(3000)

            if await self._is_logged_in():
                logger.info("✅ 已登录")
                return True

            logger.warning("❌ 未登录")
            return False
        except Exception as e:
            logger.error(f"检查登录失败: {e}")
            return False
    
    async def login_by_qrcode(self):
        """扫码登录"""
        logger.info("启动扫码登录...")
        await self.page.goto("https://www.zhihu.com/signin")
        
        try:
            # 点击扫码登录
            qrcode_tab = await self.page.query_selector('[data-za-detail-view-element_name="扫码登录"]')
            if qrcode_tab:
                await qrcode_tab.click()
                await self.page.wait_for_timeout(1000)
            
            await self.page.wait_for_selector('canvas, img[src*="qrcode"]', timeout=30000)
            # 尽量把二维码保存为图片，便于在无头/远程场景扫码
            try:
                await self.page.screenshot(path="qrcode.png")
                logger.info("二维码已保存到 qrcode.png（请用知乎 App 扫码并在手机端确认登录）")
            except Exception:
                logger.info("请扫描二维码登录（2分钟内有效）...")
        except:
            logger.warning("等待二维码失败，请手动操作")

        ok = await self._wait_for_login(timeout_ms=180000)
        if not ok:
            logger.error("❌ 登录超时（未检测到登录态）。可能原因：未在手机端确认、页面结构变更、或触发风控验证。")
            raise TimeoutError("login timeout")

        logger.info("✅ 登录成功！开始保存 Cookie...")
        await self.save_cookies()
    
    async def _try_selectors(self, selectors: List[str], timeout: int = 5000) -> Optional[Any]:
        """尝试多个选择器，返回第一个成功的"""
        for selector in selectors:
            try:
                elem = await self.page.wait_for_selector(selector, timeout=timeout)
                if elem:
                    return elem
            except:
                continue
        return None
    
    async def get_invitations(self) -> List[Invitation]:
        """获取邀请回答列表"""
        logger.info("正在获取邀请列表...")
        invitations = []
        
        try:
            # 访问通知页面
            await self.page.goto("https://www.zhihu.com/notifications", wait_until='networkidle')
            await self.page.wait_for_timeout(5000)

            if "account/unhuman" in (self.page.url or ""):
                logger.error(
                    "通知页被重定向到安全验证页面（/account/unhuman）。"
                    "请先在浏览器中完成验证后再重试。"
                )
                return []
            
            # 保存调试信息
            html = await self.page.content()
            Path('debug_notifications.html').write_text(html, encoding='utf-8')
            
            # 尝试多种选择器获取通知列表
            items = []
            for selector in NOTIFICATION_SELECTORS:
                items = await self.page.query_selector_all(selector)
                if items:
                    logger.info(f"使用选择器 '{selector}' 找到 {len(items)} 个通知")
                    break
            
            if not items:
                logger.warning("未找到任何通知，可能是页面结构变化")
                return []
            
            for item in items:
                try:
                    text = await item.text_content() or ""
                    
                    # 检查是否是邀请
                    is_invitation = any(kw in text for kw in INVITATION_KEYWORDS)
                    if not is_invitation:
                        continue
                    
                    # 提取问题链接
                    link_elem = None
                    for selector in QUESTION_LINK_SELECTORS:
                        link_elem = await item.query_selector(selector)
                        if link_elem:
                            break
                    
                    if not link_elem:
                        continue
                    
                    href = await link_elem.get_attribute('href') or ""
                    title = await link_elem.text_content() or "无标题"
                    
                    # 处理链接
                    if href.startswith('/'):
                        href = f"https://www.zhihu.com{href}"
                    
                    # 提取问题ID
                    match = re.search(r'/question/(\d+)', href)
                    if not match:
                        continue
                    
                    question_id = match.group(1)
                    
                    # 检查是否已处理
                    if question_id in self.processed_ids:
                        logger.info(f"跳过已处理: {title[:40]}...")
                        continue
                    
                    invitation = Invitation(
                        question=Question(
                            id=question_id,
                            title=title.strip(),
                            url=f"https://www.zhihu.com/question/{question_id}"
                        )
                    )
                    invitations.append(invitation)
                    logger.info(f"📌 发现邀请: {title.strip()[:60]}...")
                    
                except Exception as e:
                    logger.debug(f"解析通知项失败: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"获取邀请列表失败: {e}")
        
        logger.info(f"共发现 {len(invitations)} 个新邀请")
        return invitations
    
    async def get_question_detail(self, question: Question) -> str:
        """获取问题详情"""
        logger.info(f"获取问题详情: {question.title[:50]}...")
        
        try:
            await self.page.goto(question.url, wait_until='networkidle')
            await self.page.wait_for_timeout(3000)
            
            # 尝试多种选择器获取问题描述
            for selector in QUESTION_CONTENT_SELECTORS:
                elem = await self.page.query_selector(selector)
                if elem:
                    content = await elem.text_content()
                    question.content = (content or "").strip()[:2000]
                    logger.info(f"✅ 获取到详情，长度: {len(question.content)}")
                    return question.content
            
            logger.warning("未找到问题详情")
            return ""
            
        except Exception as e:
            logger.error(f"获取详情失败: {e}")
            return ""
    
    async def generate_answer(self, question: Question) -> str:
        """生成回答"""
        logger.info("正在生成回答...")
        
        command_template = self.config.get('answer_generator', {}).get('command', '')
        if not command_template or 'echo' in command_template:
            logger.warning("未配置回答生成工具，返回测试回答")
            return f"这是一个关于「{question.title[:50]}」的测试回答。请配置实际工具。"
        
        command = command_template
        command = command.replace('{title}', f'"{question.title}"')
        command = command.replace('{content}', f'"{question.content[:500]}"')
        
        try:
            result = subprocess.run(
                command, shell=True, capture_output=True, 
                text=True, timeout=120
            )
            
            if result.returncode != 0:
                logger.error(f"生成失败: {result.stderr}")
                return ""
            
            answer = result.stdout.strip()
            logger.info(f"✅ 回答生成完成，长度: {len(answer)}")
            return answer
            
        except Exception as e:
            logger.error(f"生成回答失败: {e}")
            return ""
    
    async def save_answer_to_draft(self, question: Question, answer: str) -> bool:
        """保存回答到草稿箱"""
        logger.info(f"正在保存到草稿箱: {question.title[:50]}...")
        
        try:
            # 访问问题页面
            await self.page.goto(question.url, wait_until='networkidle')
            await self.page.wait_for_timeout(3000)
            
            # 点击"写回答"按钮
            write_btn = None
            for selector in WRITE_ANSWER_BUTTONS:
                write_btn = await self.page.query_selector(selector)
                if write_btn:
                    logger.info(f"找到写回答按钮: {selector}")
                    break
            
            if write_btn:
                await write_btn.click()
                await self.page.wait_for_timeout(3000)
            else:
                # 直接访问写回答页面
                write_url = f"https://www.zhihu.com/question/{question.id}/write"
                await self.page.goto(write_url, wait_until='networkidle')
                await self.page.wait_for_timeout(3000)
            
            # 查找编辑器
            editor = None
            for selector in EDITOR_SELECTORS:
                editor = await self.page.query_selector(selector)
                if editor:
                    logger.info(f"找到编辑器: {selector}")
                    break
            
            if not editor:
                logger.error("未找到编辑器")
                return False
            
            # 输入回答
            await editor.click()
            await self.page.wait_for_timeout(500)
            await self.page.keyboard.press('Control+a')
            await self.page.wait_for_timeout(200)
            await self.page.keyboard.press('Delete')
            await self.page.wait_for_timeout(200)
            await editor.fill(answer)
            await self.page.wait_for_timeout(3000)
            
            # 保存草稿
            for selector in SAVE_DRAFT_BUTTONS:
                draft_btn = await self.page.query_selector(selector)
                if draft_btn:
                    await draft_btn.click()
                    logger.info("点击保存草稿按钮")
                    await self.page.wait_for_timeout(3000)
                    break
            else:
                # 知乎自动保存，等待一下
                await self.page.wait_for_timeout(5000)
                logger.info("等待自动保存...")
            
            logger.info("✅ 回答已保存到草稿箱")
            return True
            
        except Exception as e:
            logger.error(f"保存回答失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    async def send_notification(self, message: str):
        """发送通知"""
        webhook = self.config.get('notification', {}).get('feishu_webhook', '')
        if not webhook:
            logger.info("未配置飞书 webhook")
            return
        
        try:
            import requests
            response = requests.post(webhook, json={
                "msg_type": "text",
                "content": {"text": message}
            }, timeout=10)
            
            if response.status_code == 200:
                logger.info("✅ 飞书通知已发送")
            else:
                logger.warning(f"飞书通知失败: {response.status_code}")
        except Exception as e:
            logger.error(f"发送通知失败: {e}")
    
    async def process_invitations(self):
        """处理所有邀请"""
        invitations = await self.get_invitations()
        
        if not invitations:
            logger.info("📭 没有新的邀请")
            return
        
        processed = []
        failed = []
        
        for i, invitation in enumerate(invitations):
            logger.info(f"\n处理第 {i+1}/{len(invitations)} 个邀请...")
            
            try:
                # 获取问题详情
                await self.get_question_detail(invitation.question)
                
                # 生成回答
                answer = await self.generate_answer(invitation.question)
                if not answer:
                    failed.append(invitation.question.title)
                    continue
                
                # 保存到草稿
                success = await self.save_answer_to_draft(invitation.question, answer)
                
                if success:
                    processed.append({
                        'title': invitation.question.title,
                        'url': invitation.question.url
                    })
                    self.processed_ids.add(invitation.question.id)
                    self._save_processed_ids()
                else:
                    failed.append(invitation.question.title)
                
                await asyncio.sleep(10)
                
            except Exception as e:
                logger.error(f"处理邀请失败: {e}")
                failed.append(invitation.question.title)
        
        # 发送通知
        if processed or failed:
            message = f"🤖 知乎自动回答机器人\n\n"
            message += f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
            
            if processed:
                message += f"✅ 成功 {len(processed)} 个:\n"
                for item in processed:
                    message += f"\n📌 {item['title'][:50]}...\n"
                message += "\n请登录知乎查看草稿箱。\n"
            
            if failed:
                message += f"\n❌ 失败 {len(failed)} 个\n"
            
            await self.send_notification(message)
    
    async def close(self):
        """关闭浏览器"""
        try:
            if self.context:
                await self.context.close()
        except Exception as e:
            logger.warning(f"关闭 context 失败: {e}")

        try:
            if self.browser:
                await self.browser.close()
        except Exception as e:
            logger.warning(f"关闭 browser 失败: {e}")

        if self.playwright:
            await self.playwright.stop()
        logger.info("浏览器已关闭")
