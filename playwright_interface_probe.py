#!/usr/bin/env python3
"""
Playwright 接口联调脚本（人工验证 + 自动复测）。

用途：
1) 使用本地 zhihu_cookies.json 打开知乎；
2) 如果被重定向到 /account/unhuman，等待用户在浏览器窗口完成验证；
3) 验证通过后，调用关键接口并输出结果：
   - /api/v4/me
   - /api/v4/me/invitations
"""
import argparse
import asyncio
import json
from pathlib import Path
from typing import Any, Dict, List

from playwright.async_api import async_playwright


COOKIE_FILE = Path("zhihu_cookies.json")


def _normalize_invitations(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    兼容知乎 invitations 接口多种返回结构：
    - {"data": [ ... ]}
    - {"data": {"invitation": [ ... ]}}
    - {"data": {"xxx": [ ... ]}}
    """
    data = payload.get("data")
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]

    if isinstance(data, dict):
        if isinstance(data.get("invitation"), list):
            return [x for x in data["invitation"] if isinstance(x, dict)]

        for _, value in data.items():
            if isinstance(value, list):
                return [x for x in value if isinstance(x, dict)]

    return []


async def _api_get_json(context, url: str):
    resp = await context.request.get(url)
    status = resp.status
    text = await resp.text()
    try:
        data = json.loads(text)
    except Exception:
        data = None
    return status, data, text


async def main():
    parser = argparse.ArgumentParser(description="Playwright 接口联调（含风控验证）")
    parser.add_argument("--headless", action="store_true", help="无头模式（默认有界面，便于人工验证）")
    parser.add_argument("--wait-seconds", type=int, default=300, help="等待人工验证最长秒数")
    args = parser.parse_args()

    if not COOKIE_FILE.exists():
        print("❌ 缺少 zhihu_cookies.json，请先执行登录流程。")
        raise SystemExit(2)

    cookies = json.loads(COOKIE_FILE.read_text(encoding="utf-8"))

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=args.headless)
        context = await browser.new_context(
            viewport={"width": 1440, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            locale="zh-CN",
            timezone_id="Asia/Shanghai",
        )
        await context.add_cookies(cookies)
        page = await context.new_page()

        print("1) 打开通知页...")
        await page.goto("https://www.zhihu.com/notifications", wait_until="networkidle")
        await page.wait_for_timeout(1000)
        print(f"   当前 URL: {page.url}")

        deadline = asyncio.get_event_loop().time() + args.wait_seconds
        while "account/unhuman" in page.url:
            remain = int(deadline - asyncio.get_event_loop().time())
            if remain <= 0:
                print("❌ 等待验证超时。请重新运行脚本并在浏览器中完成验证。")
                await browser.close()
                raise SystemExit(1)

            print(f"⚠️ 检测到风控验证页，请在浏览器窗口完成验证。剩余 {remain}s")
            await page.wait_for_timeout(5000)
            # 轮询当前页面状态
            try:
                await page.reload(wait_until="domcontentloaded")
                await page.wait_for_timeout(1000)
                print(f"   验证后 URL: {page.url}")
            except Exception:
                # 某些验证流程会暂时阻断 reload，这里容错等待
                pass

        print("2) 风控页已通过，开始调用关键接口...")
        me_status, me_json, _ = await _api_get_json(context, "https://www.zhihu.com/api/v4/me")
        inv_status, inv_json, inv_text = await _api_get_json(
            context, "https://www.zhihu.com/api/v4/me/invitations?limit=20&offset=0"
        )

        print(f"   /api/v4/me -> status={me_status}")
        me_name = me_json.get("name") if isinstance(me_json, dict) else None
        print(f"   me.name={me_name}")

        print(f"   /api/v4/me/invitations -> status={inv_status}")
        invitations = _normalize_invitations(inv_json or {})
        print(f"   invitations_parsed={len(invitations)}")
        if invitations:
            first = invitations[0]
            q = first.get("question") if isinstance(first, dict) else None
            if isinstance(q, dict):
                print(f"   first_question_id={q.get('id')}")
                print(f"   first_question_title={q.get('title')}")
        elif isinstance(inv_json, dict) and "error" in inv_json:
            err = inv_json.get("error", {})
            if isinstance(err, dict):
                print(f"   invitations_error_code={err.get('code')}")
                print(f"   invitations_error_message={err.get('message')}")
        else:
            print(f"   invitations_raw_prefix={inv_text[:220]}")

        Path("debug_me.json").write_text(
            json.dumps({"status": me_status, "body": me_json}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        Path("debug_invitations.json").write_text(
            json.dumps({"status": inv_status, "body": inv_json}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print("3) 调试输出已保存：debug_me.json / debug_invitations.json")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
