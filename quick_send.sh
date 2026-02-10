#!/bin/bash
# 快速生成知乎二维码并发送邮件

cd /home/node/.openclaw/workspace/zhihu-auto-answer
. venv/bin/activate

# 启动程序生成二维码（后台运行）
python zhihu_bot_headless.py &
BOT_PID=$!

# 等待二维码生成
echo "正在生成二维码..."
for i in {1..15}; do
    if [ -f qrcode.png ] && [ $(stat -c%s qrcode.png) -gt 1000 ]; then
        echo "✅ 二维码已生成"
        break
    fi
    sleep 1
done

# 立即发送邮件
echo "正在发送邮件..."
cd /home/node/.openclaw/workspace/skills/email-sender
python3 email_sender.py "1781051483@qq.com" "知乎二维码 - 快速" "新鲜生成的知乎二维码，请立即扫描！" "/home/node/.openclaw/workspace/zhihu-auto-answer/qrcode.png"

echo "📧 邮件已发送，请立即查收并扫码！"
echo "⏳ 程序正在后台等待扫码（PID: $BOT_PID）"

# 等待程序结束
wait $BOT_PID
