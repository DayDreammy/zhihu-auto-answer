#!/usr/bin/env python3
"""
快速测试 - 验证Cookie和基本功能
"""
import sys
sys.path.insert(0, '.')

from zhihu_bot_v2 import ZhihuAutoAnswer


def test_cookie():
    """测试Cookie是否有效"""
    print("=" * 60)
    print("知乎Cookie测试")
    print("=" * 60)
    
    bot = ZhihuAutoAnswer()
    
    # 尝试加载Cookie
    if not bot.load_cookies_from_file():
        print("\n❌ 没有找到Cookie文件")
        print("\n请使用以下方法之一提供Cookie:")
        print("  1. 运行: python zhihu_bot_v2.py --login")
        print("  2. 从浏览器导出Cookie到 zhihu_cookies.json")
        print("  3. 使用: python test_cookie.py --cookie-string 'z_c0=xxx; xxx=xxx'")
        return False
    
    # 测试登录
    print("\n测试登录状态...")
    if bot.check_login():
        print("\n✅ Cookie有效！")
        
        # 测试获取邀请
        print("\n测试获取邀请列表...")
        invitations = bot.get_invitations()
        
        if invitations:
            print(f"\n✅ 发现 {len(invitations)} 个新邀请:")
            for inv in invitations:
                print(f"  📌 {inv.question.title[:60]}...")
        else:
            print("\n📭 没有新的邀请（或所有邀请都已处理）")
        
        return True
    else:
        print("\n❌ Cookie已失效，请重新登录")
        return False


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument('--cookie-string', help='从命令行提供Cookie字符串')
    args = parser.parse_args()
    
    if args.cookie_string:
        bot = ZhihuAutoAnswer()
        bot.load_cookies_from_string(args.cookie_string)
        if bot.check_login():
            print("✅ Cookie有效！")
            invitations = bot.get_invitations()
            print(f"发现 {len(invitations)} 个邀请")
        else:
            print("❌ Cookie无效")
    else:
        test_cookie()
