# 知乎自动回答机器人 - 快速开始

## 📁 项目结构

```
zhihu-auto-answer/
├── main.py              # 主程序入口
├── zhihu_bot.py         # 核心机器人逻辑
├── analyze.py           # 页面结构分析工具
├── config.yaml          # 配置文件
├── requirements.txt     # Python 依赖
├── run.sh              # 定时任务脚本
├── logs/               # 日志目录
├── zhihu_cookies.json  # Cookie 文件（自动生成）
└── processed_invitations.json  # 已处理问题记录
```

## 🚀 快速开始

### 1. 安装依赖

```bash
# 安装 Python 依赖
pip install -r requirements.txt

# 安装 Playwright 浏览器
playwright install chromium
```

### 2. 配置回答生成工具

编辑 `config.yaml`：

```yaml
answer_generator:
  # 配置你的回答生成工具命令
  # 示例1: 直接调用脚本
  command: "python /path/to/your_answer_tool.py --title '{title}' --content '{content}'"
  
  # 示例2: 调用 API
  # command: "curl -X POST http://localhost:8000/generate -d 'question={title}'"
```

### 3. 首次登录

```bash
# 启动扫码登录
python main.py --login
```

- 程序会打开浏览器窗口
- 显示知乎登录二维码
- 用手机知乎 App 扫码
- 登录成功后 Cookie 自动保存

### 4. 运行测试

```bash
# 运行一次，检查邀请并处理
python main.py
```

### 5. 配置定时任务

```bash
# 编辑 crontab
crontab -e

# 添加每12小时运行一次
0 */12 * * * cd /path/to/zhihu-auto-answer && python main.py >> logs/cron.log 2>&1
```

## 🔧 调试和排错

### 页面结构分析

如果程序无法找到邀请或编辑器，运行分析工具：

```bash
python analyze.py
```

按提示操作，程序会：
1. 打开知乎通知页面
2. 让你登录
3. 分析页面结构
4. 保存 HTML 到 `debug_notifications.html`

### 查看日志

```bash
# 实时查看日志
tail -f logs/zhihu_bot.log
```

### 常见问题

**Q: 提示"未登录"**
- 先运行 `python main.py --login` 扫码登录

**Q: 找不到邀请**
- 确保知乎账号有未处理的邀请
- 运行 `python analyze.py` 分析页面结构

**Q: 找不到编辑器**
- 知乎可能更新了页面结构
- 运行分析工具确认选择器

**Q: 回答未保存到草稿**
- 检查回答内容是否为空
- 查看日志中的错误信息

## 📝 更新记录

### v1.0.0
- ✅ 登录功能（Cookie/扫码）
- ✅ 邀请检测
- ✅ 问题详情获取
- ✅ 外部工具调用
- ✅ 保存到草稿箱
- ✅ 飞书通知
- ✅ 去重处理（避免重复回答）
