#!/usr/bin/env python3
"""
Cookie/登录相关脚本 + 可选集成测试。

注意：访问知乎需要有效 Cookie，且会触发网络请求/风控校验；
默认 pytest 不跑集成测试，避免 CI/本地无 Cookie 时误报失败。
"""
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, ".")


def test_import_zhihu_bot_creates_logs_dir():
    # 这是一个纯本地单元测试：保证核心模块可导入，且不会因为 logs/ 缺失而崩溃。
    import zhihu_bot  # noqa: F401

    assert Path("logs").exists()


@pytest.mark.skipif(
    os.environ.get("ZHIHU_INTEGRATION") != "1",
    reason="requires network + valid zhihu cookies; set env ZHIHU_INTEGRATION=1 to enable",
)
def test_cookie_integration():
    """集成测试：验证 Cookie 是否有效（需要提前准备 zhihu_cookies.json）。"""
    from zhihu_bot_v2 import ZhihuAutoAnswer

    bot = ZhihuAutoAnswer()
    assert bot.load_cookies_from_file(), "Cookie 文件不存在或无法解析"
    assert bot.check_login(), "Cookie 无效或已过期"


def _cli():
    from zhihu_bot_v2 import ZhihuAutoAnswer

    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--cookie-string", help="从命令行提供Cookie字符串")
    args = parser.parse_args()

    bot = ZhihuAutoAnswer()

    if args.cookie_string:
        bot.load_cookies_from_string(args.cookie_string)
    else:
        if not bot.load_cookies_from_file():
            print("❌ 没有找到 Cookie 文件: zhihu_cookies.json")
            print("可选方案:")
            print("  1) python main.py --login  (推荐，扫码保存 Playwright Cookie)")
            print("  2) python zhihu_bot_v2.py --login")
            print("  3) python test_cookie.py --cookie-string \"z_c0=...; d_c0=...\"")
            return 2

    if bot.check_login():
        print("✅ Cookie 有效")
        inv = bot.get_invitations()
        print(f"邀请数: {len(inv)}")
        return 0

    print("❌ Cookie 无效/已过期")
    return 1


if __name__ == "__main__":
    raise SystemExit(_cli())
