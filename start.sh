#!/bin/bash
# 知乎自动回答机器人启动脚本

cd "$(dirname "$0")"

# 激活虚拟环境
if [ -d "venv" ]; then
    . venv/bin/activate
fi

# 检查参数
if [ "$1" = "--login" ]; then
    echo "启动扫码登录..."
    python zhihu_bot_v2.py --login --no-headless
elif [ "$1" = "--test" ]; then
    echo "测试Cookie..."
    python test_cookie.py
else
    echo "启动知乎自动回答机器人..."
    python zhihu_bot_v2.py "$@"
fi
