#!/usr/bin/env python3
"""
知乎自动回答机器人 - 主程序 v2
"""
import asyncio
import argparse
import sys
from pathlib import Path

# Optional: load secrets (e.g. CABINET_API_TOKEN) from .env
try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass

# Avoid UnicodeEncodeError on Windows consoles (cp936/gbk) when logs contain non-ASCII.
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

# 确保可以导入本地模块
sys.path.insert(0, str(Path(__file__).parent))

from zhihu_bot import ZhihuAutoAnswer


async def main():
    parser = argparse.ArgumentParser(
        description='知乎自动回答机器人',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 扫码登录
  python main.py --login
  
  # 使用持久化浏览器目录（首次登录一次，后续可复用）
  python main.py --login --user-data-dir .playwright-profile/zhihu
  
  # 运行一次
  python main.py
  
  # 使用指定配置
  python main.py --config myconfig.yaml
        """
    )
    parser.add_argument('--login', action='store_true', help='扫码登录并保存Cookie')
    parser.add_argument('--config', default='config.yaml', help='配置文件路径')
    parser.add_argument('--headless', action='store_true', help='无界面模式（用于定时任务）')
    parser.add_argument('--max-questions', type=int, default=10, help='每次最多处理多少个问题（默认10）')
    parser.add_argument(
        '--answer-type',
        choices=['command', 'deep_research'],
        default=None,
        help='回答生成方式（覆盖 config.yaml answer_generator.type）',
    )
    parser.add_argument('--flush-drafts-every', type=int, default=5, help='每累计多少个回答写入一次草稿箱（deep_research模式）')
    parser.add_argument(
        '--user-data-dir',
        default='.playwright-profile/zhihu',
        help='Playwright持久化用户目录（默认启用，首次登录后后续可直接复用）'
    )
    parser.add_argument(
        '--no-persistent-profile',
        action='store_true',
        help='禁用持久化用户目录，仅使用临时浏览器+cookie文件'
    )
    args = parser.parse_args()
    
    bot = ZhihuAutoAnswer(config_path=args.config)
    
    try:
        # 允许 CLI 覆盖回答生成方式
        if args.answer_type:
            bot.config.setdefault('answer_generator', {})
            bot.config['answer_generator']['type'] = args.answer_type

        # 初始化浏览器
        user_data_dir = None if args.no_persistent_profile else args.user_data_dir
        await bot.init_browser(headless=args.headless, user_data_dir=user_data_dir)
        
        if args.login:
            await bot.login_by_qrcode()
            if user_data_dir:
                print(f"\n✅ 登录完成，浏览器资料已持久化到: {user_data_dir}")
                print("✅ 下次可直接运行 `python main.py` 复用登录态")
            print("✅ Cookie 备份已保存到 zhihu_cookies.json")
            return
        
        # 检查登录状态
        if not await bot.check_login():
            print("\n❌ 未登录，请先运行: python main.py --login")
            # 仍然发送通知，避免定时任务“静默失败”
            summary = {
                "run_id": "not_logged_in",
                "started_at": "",
                "ended_at": "",
                "mode": "not_logged_in",
                "selected": 0,
                "draft_saved_ok": 0,
                "failures": [{"stage": "check_login", "title": "not_logged_in"}],
                "artifacts": {},
            }
            try:
                await bot.send_notification("🤖 知乎自动回答机器人\n\n未登录：请先运行 python main.py --login\n")
            except Exception:
                pass
            return
        
        # 处理邀请（返回 summary）
        summary = await bot.process_invitations(
            max_questions=args.max_questions,
            flush_drafts_every=args.flush_drafts_every,
        )

        # 无论成功失败，都发一条相对详细的通知
        try:
            # log tail
            log_path = Path("logs") / "zhihu_bot.log"
            tail = ""
            if log_path.exists():
                try:
                    tail_lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()[-60:]
                    tail = "\n".join(tail_lines)
                except Exception:
                    tail = ""

            msg = []
            msg.append("🤖 知乎自动回答机器人")
            msg.append(f"⏰ run_id={summary.get('run_id')} started={summary.get('started_at')} ended={summary.get('ended_at')}")
            msg.append(f"mode={summary.get('mode')} selected={summary.get('selected')} draft_saved_ok={summary.get('draft_saved_ok')}")
            fails = summary.get("failures") or []
            msg.append(f"failures={len(fails)}")
            if fails:
                msg.append("失败明细(最多10条):")
                for item in fails[:10]:
                    title = item.get("title") or ""
                    stage = item.get("stage") or ""
                    status = item.get("status")
                    msg.append(f"- [{stage}] {title[:60]} status={status}")
            art = summary.get("artifacts") or {}
            if art:
                msg.append(f"artifacts: {art}")
            if tail:
                msg.append("\nlog_tail:\n" + tail)

            await bot.send_notification("\n".join(msg))
        except Exception:
            pass
        
    except KeyboardInterrupt:
        print("\n\n👋 程序已停止")
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        try:
            await bot.send_notification(f"🤖 知乎自动回答机器人\n\n运行异常: {type(e).__name__}: {e}\n")
        except Exception:
            pass
    finally:
        await bot.close()


if __name__ == '__main__':
    asyncio.run(main())
