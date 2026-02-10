# 知乎自动回答机器人 - 使用说明

## 环境要求
- Python 3.8+
- 安装依赖: `pip install playwright pyyaml requests`
- 安装浏览器: `playwright install chromium`

## 快速开始

### 第一步：获取Cookie

#### 方法1：扫码登录（推荐）
```bash
cd /home/node/.openclaw/workspace/zhihu-auto-answer
. venv/bin/activate
python zhihu_bot_v2.py --login --no-headless
```
- 程序会打开浏览器窗口
- 显示知乎登录二维码
- 用手机知乎App扫码
- 登录成功后Cookie自动保存到 `zhihu_cookies.json`

#### 方法2：从浏览器导出Cookie
1. 在浏览器中登录知乎
2. 打开开发者工具 (F12) -> Application/应用 -> Cookies
3. 导出Cookie或复制关键字段（如 `z_c0`, `_xsrf`）
4. 保存到 `zhihu_cookies.json` 文件

### 第二步：测试Cookie
```bash
python test_cookie.py
```
- 验证Cookie是否有效
- 检查是否能获取到邀请列表

### 第三步：配置回答生成工具

编辑 `config.yaml`:
```yaml
answer_generator:
  command: "你的回答生成工具命令 '{title}' '{content}'"
  
notification:
  feishu_webhook: "你的飞书webhook地址"
```

### 第四步：运行
```bash
# 有界面模式（调试）
python zhihu_bot_v2.py --no-headless

# 无界面模式（生产）
python zhihu_bot_v2.py --headless
```

## 工作原理

1. **获取邀请** - 调用知乎API `/api/v4/me/invitations` 获取邀请列表
2. **生成回答** - 调用你配置的外部工具生成回答内容
3. **保存草稿** - 使用Playwright自动化浏览器，将回答写入知乎草稿箱
4. **发送通知** - 通过飞书通知你审核

## 文件说明

| 文件 | 说明 |
|------|------|
| `zhihu_bot_v2.py` | 主程序（核心代码） |
| `test_cookie.py` | Cookie测试工具 |
| `zhihu_cookies.json` | Cookie文件（自动生成） |
| `processed_invitations.json` | 已处理邀请记录 |
| `config.yaml` | 配置文件 |

## 常见问题

### Q: 提示"未登录"
- Cookie已过期，重新运行 `--login` 扫码
- 检查Cookie文件是否正确

### Q: 获取不到邀请
- 确认知乎账号真的有未处理的邀请
- 运行 `test_cookie.py` 检查API调用

### Q: 无法保存到草稿箱
- 可能是知乎页面结构变化
- 尝试更新代码中的选择器
- 或者使用 `--no-headless` 观察浏览器行为

## 安全提示
- Cookie文件包含敏感信息，不要上传到公共仓库
- 建议添加到 `.gitignore`
- 定期更换知乎密码
