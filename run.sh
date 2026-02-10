#!/bin/bash
# 知乎自动回答机器人定时任务脚本
# 添加到 crontab: 0 */12 * * * /path/to/run.sh

cd "$(dirname "$0")"

# 激活虚拟环境（如果有）
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# 运行主程序
python main.py >> logs/zhihu_bot.log 2>&1
