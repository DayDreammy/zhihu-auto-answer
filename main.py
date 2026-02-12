#!/usr/bin/env python3
"""
知乎自动回答机器人 - 主程序 v2
"""
import asyncio
import argparse
import sys
from pathlib import Path

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
            return
        
        # 处理邀请
        await bot.process_invitations()
        
    except KeyboardInterrupt:
        print("\n\n👋 程序已停止")
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await bot.close()


if __name__ == '__main__':
    asyncio.run(main())
