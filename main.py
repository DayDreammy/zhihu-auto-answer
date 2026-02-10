#!/usr/bin/env python3
"""
知乎自动回答机器人 - 主程序 v2
"""
import asyncio
import argparse
import sys
from pathlib import Path

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
  
  # 运行一次
  python main.py
  
  # 使用指定配置
  python main.py --config myconfig.yaml
        """
    )
    parser.add_argument('--login', action='store_true', help='扫码登录并保存Cookie')
    parser.add_argument('--config', default='config.yaml', help='配置文件路径')
    parser.add_argument('--headless', action='store_true', help='无界面模式（用于定时任务）')
    args = parser.parse_args()
    
    bot = ZhihuAutoAnswer(config_path=args.config)
    
    try:
        # 初始化浏览器
        await bot.init_browser(headless=args.headless)
        
        if args.login:
            await bot.login_by_qrcode()
            print("\n✅ 登录完成，Cookie 已保存到 zhihu_cookies.json")
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
