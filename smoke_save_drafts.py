#!/usr/bin/env python3
"""
Smoke test: 批量把前 N 个「邀请回答」写入草稿箱（占位内容）。

特点：
- 使用 Playwright 持久化用户目录（user-data-dir）复用登录态
- 支持有头模式手动通过 /account/unhuman 风控验证
- 从通知页解析邀请，去重后取前 N 个
- 对每个问题：获取详情 -> 写回答 -> 保存草稿，并输出汇总

示例：
  python smoke_save_drafts.py --n 5 --headed
  python smoke_save_drafts.py --n 5 --user-data-dir .playwright-profile/zhihu --headless
"""

import argparse
import asyncio
from datetime import datetime

from zhihu_bot import ZhihuAutoAnswer


async def wait_manual_verify(page, max_seconds: int) -> bool:
    """如果落在 unhuman 验证页，等待用户手动完成验证（不自动刷新）。"""
    elapsed = 0
    while elapsed < max_seconds:
        if page.is_closed():
            return False
        url = page.url or ""
        if "account/unhuman" not in url:
            return True
        print(f"waiting_manual_verify... elapsed={elapsed}s url={url}")
        await page.wait_for_timeout(5000)
        elapsed += 5
    return False


async def main():
    ap = argparse.ArgumentParser(description="Zhihu draft smoke test (Playwright)")
    ap.add_argument("--n", type=int, default=5, help="保存草稿数量")
    ap.add_argument(
        "--user-data-dir",
        default=".playwright-profile/zhihu",
        help="Playwright 持久化用户目录（推荐）",
    )
    ap.add_argument("--headed", action="store_true", help="有头模式（便于手动验证）")
    ap.add_argument("--headless", action="store_true", help="无头模式")
    ap.add_argument("--verify-wait-seconds", type=int, default=600, help="手动验证等待秒数")
    args = ap.parse_args()

    # 默认使用有头模式，除非显式 --headless
    headless = args.headless and not args.headed

    bot = ZhihuAutoAnswer()
    await bot.init_browser(headless=headless, user_data_dir=args.user_data_dir)

    results = []
    try:
        ok = await bot.check_login()
        print(f"login_ok={ok}")
        if not ok:
            print("not_logged_in: please run `python main.py --login --user-data-dir ...` first")
            return 2

        # 打开通知页，如果触发 unhuman，等用户手动过验证
        await bot.page.goto("https://www.zhihu.com/notifications", wait_until="domcontentloaded")
        if "account/unhuman" in (bot.page.url or ""):
            passed = await wait_manual_verify(bot.page, args.verify_wait_seconds)
            print(f"verify_passed={passed} url={bot.page.url}")
            if not passed:
                print("verify_timeout_or_page_closed")
                return 1

        invitations = await bot.get_invitations()
        print(f"invitations_found={len(invitations)}")
        if not invitations:
            print("no_invitations")
            return 0

        # 去重后取前 N
        unique = []
        seen = set()
        for inv in invitations:
            qid = inv.question.id
            if qid and qid not in seen:
                seen.add(qid)
                unique.append(inv)
            if len(unique) >= args.n:
                break

        print(f"target_count={len(unique)}")
        for idx, inv in enumerate(unique, 1):
            q = inv.question
            print(f"[{idx}] question_id={q.id} title={q.title}")

            await bot.get_question_detail(q)
            answer = (
                "【自动化测试草稿】\n\n"
                f"问题：{q.title}\n\n"
                "这是一条用于联调验证的占位回答内容。\n"
                f"时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            )

            save_ok = await bot.save_answer_to_draft(q, answer)
            results.append((q.id, q.title, save_ok))
            print(f"[{idx}] save_ok={save_ok}")

            await asyncio.sleep(2)

        success = sum(1 for _, _, ok in results if ok)
        failed = len(results) - success
        print("=== summary ===")
        print(f"success={success} failed={failed}")
        for qid, title, ok in results:
            print(f"- {qid} | {'OK' if ok else 'FAIL'} | {title}")

        return 0 if failed == 0 else 1

    finally:
        await bot.close()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

