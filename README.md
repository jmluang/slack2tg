# Slack to Telegram Forwarder

将 Slack Channel 的消息实时转发到 Telegram Channel 的 Bot。

## 功能特点

- 实时消息转发（使用 Slack Socket Mode）
- 一对一 Channel 映射
- 显示发送者名称（支持用户和 Bot）
- 支持消息附件转发
- Docker 容器化部署 / 本地 Python 运行
- 调试模式可配置
- 敏感信息不输出日志

## 快速开始

### 1. 创建 Slack App

1. 访问 [Slack API](https://api.slack.com/apps) 创建新 App
2. 选择 "From scratch"
3. 启用 **Socket Mode**:
   - 进入 `Socket Mode` → 启用
   - 生成 `App-Level Token` (scopes: `connections:write`)
4. 启用 **Bot Token**:
   - 进入 `OAuth & Permissions` → `Scopes`
   - 添加 `chat:write`, `channels:read`, `groups:read`, `users:read`
   - 安装 App 到工作区，获取 `Bot Token`
5. 订阅事件:
   - 进入 `Event Subscriptions` → 启用
   - 订阅 `message.channels` 和 `message.groups`
   - 重新安装 App

### 2. 创建 Telegram Bot

1. 在 Telegram 中找 @BotFather
2. 发送 `/newbot` 创建新 Bot
3. 获取 Bot Token (格式: `123456789:ABCdef...`)
4. 将 Bot 添加到目标 Channel 作为管理员

### 3. 获取 Channel ID

**Slack Channel ID:**
- 在 Slack 中打开 Channel
- 点击 Channel 名称 → About → 底部显示 Channel ID (以 C 开头)

**Telegram Chat ID:**
- 私人群组: 使用 @userinfobot 或 https://api.telegram.org/bot<TOKEN>/getUpdates 查看
- 公开频道: 使用 @channelusername 格式

### 4. 配置

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，填入你的 Token
nano .env
```

### 5. 运行

**方式一：本地运行（推荐测试用）**

```bash
# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# 启动
python3 main.py
```

**方式二：Docker 运行（推荐生产环境）**

```bash
docker-compose up -d
```

## 配置说明

### 环境变量 (.env)

```bash
# Slack 配置
SLACK_APP_TOKEN=xapp-xxxxxxxxxx
SLACK_BOT_TOKEN=xoxb-xxxxxxxxxx

# Telegram 配置
TELEGRAM_BOT_TOKEN=123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZ

# Channel 映射
SLACK_CHANNEL_ID=C0123456789
TELEGRAM_CHANNEL=-1001234567890

# 调试模式 (true/false)
# true: 输出详细日志
# false: 只输出基本日志
APP_DEBUG=false
```

### Channel 映射 (config.yaml)

也可以在 `config.yaml` 中配置：

```yaml
channel_mappings:
  ${SLACK_CHANNEL_ID}: "${TELEGRAM_CHANNEL}"
  # 或直接写死：
  # C0123456789: "-1001234567890"
```

支持环境变量语法：`${VAR}` 或 `${VAR:-default}`

## 项目结构

```
.
├── main.py                 # 主程序入口
├── src/
│   ├── config.py          # 配置管理
│   ├── slack_handler.py   # Slack 消息处理
│   └── telegram_sender.py # Telegram 消息发送
├── config.yaml            # Channel 映射配置
├── .env                   # 环境变量（需自行创建）
├── .env.example           # 环境变量模板
├── requirements.txt       # Python 依赖
├── Dockerfile            # Docker 镜像定义
├── docker-compose.yml    # Docker Compose 配置
├── test_telegram.py      # Telegram 测试脚本
└── README.md             # 本文档
```

## 环境变量说明

| 变量名 | 说明 | 获取方式 |
|--------|------|----------|
| `SLACK_APP_TOKEN` | Slack App-Level Token | Slack App → Socket Mode |
| `SLACK_BOT_TOKEN` | Slack Bot Token | Slack App → OAuth & Permissions |
| `TELEGRAM_BOT_TOKEN` | Telegram Bot Token | @BotFather |
| `SLACK_CHANNEL_ID` | Slack Channel ID | Slack Channel → About |
| `TELEGRAM_CHANNEL` | Telegram Chat ID | @userinfobot 或 getUpdates |
| `APP_DEBUG` | 调试模式 | true/false |

## 故障排查

**1. 无法接收 Slack 消息**
- 确认 App 已安装到目标 Channel
- 检查 Event Subscriptions 是否订阅了正确的事件
- 在 Slack 输入 `/invite @你的Bot名称`

**2. 无法发送到 Telegram**
- 确认 Bot 已是目标 Channel 的管理员
- 检查 Chat ID 是否正确
- 运行 `python test_telegram.py` 测试 Bot

**3. 本地运行 SSL 证书错误**
- macOS: 运行 `/Applications/Python\ 3.x/Install\ Certificates.command`
- 或设置 `SSL_CERT_FILE` 环境变量

**4. Docker 运行问题**
- 检查 `.env` 文件是否存在且正确
- 确认 `config.yaml` 格式正确
- 查看容器日志: `docker-compose logs`

## License

MIT
