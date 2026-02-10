# 知乎自动回答机器人

🤖 自动检测知乎邀请回答，生成回复并保存到草稿箱。

## 功能

- ✅ 扫码/Cookie 登录知乎
- ✅ 自动检测邀请回答
- ✅ 调用外部工具生成回答
- ✅ 自动保存到草稿箱
- ✅ 飞书/邮件通知
- ✅ 定时任务支持

## 安装

```bash
# 克隆仓库
git clone https://github.com/yourusername/zhihu-auto-answer.git
cd zhihu-auto-answer

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
playwright install chromium
```

## 使用方法

### 1. 配置回答生成工具

编辑 `config.yaml`：

```yaml
answer_generator:
  # 配置你的回答生成工具命令
  command: "python /path/to/your_tool.py --title '{title}' --content '{content}'"
  
notification:
  feishu_webhook: "你的飞书webhook地址"
```

### 2. 运行程序

```bash
python zhihu_bot_headless.py
```

程序会：
1. 生成知乎登录二维码
2. 显示在屏幕上
3. 你用知乎App扫描
4. 自动获取邀请列表
5. 生成回答并保存到草稿箱

### 3. 定时运行

```bash
# 每12小时运行一次
crontab -e
0 */12 * * * cd /path/to/zhihu-auto-answer && python zhihu_bot_headless.py
```

## 项目结构

```
zhihu-auto-answer/
├── zhihu_bot_headless.py    # 主程序
├── zhihu_bot_cookie.py      # Cookie模式（无需扫码）
├── get_cookies.py           # 获取Cookie工具
├── config.yaml              # 配置文件
├── requirements.txt         # Python依赖
└── README.md               # 说明文档
```

## 配置Cookie模式（可选）

如果你不想每次都扫码，可以导出浏览器Cookie：

1. 在浏览器登录知乎
2. 打开开发者工具(F12) -> Console
3. 运行以下代码获取Cookie：

```javascript
const cookies = document.cookie.split(';').map(c => {
    const [name, value] = c.trim().split('=');
    return {name, value, domain: '.zhihu.com', path: '/'};
}).filter(c => ['z_c0', '_xsrf', 'd_c0'].includes(c.name));
console.log(JSON.stringify(cookies, null, 2));
```

4. 保存到 `zhihu_cookies.json`
5. 运行 `python zhihu_bot_cookie.py`

## 注意事项

- 知乎二维码有效期约2分钟，请尽快扫描
- 首次登录可能需要完成安全验证
- 建议定期更新Cookie
- 请遵守知乎使用规范

## License

MIT
