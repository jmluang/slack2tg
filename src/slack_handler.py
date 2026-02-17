import asyncio
import logging
from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
from .config import Config
from .telegram_sender import TelegramSender

logger = logging.getLogger(__name__)


class SlackHandler:
    """Slack 消息处理器"""

    def __init__(self, config: Config):
        self.config = config
        self.telegram_sender = TelegramSender(config.telegram_bot_token)
        self.app = AsyncApp(token=config.slack_bot_token)
        self._handler = None
        self._setup_handlers()

    def _setup_handlers(self):
        """设置 Slack 事件处理器"""

        # 捕获所有事件（仅在调试模式）
        @self.app.middleware
        async def log_all_events(logger, body, next):
            if self.config.debug:
                event_type = body.get("event", {}).get("type", "unknown")
                logger.debug(f"[EVENT] Received event type: {event_type}")
            await next()

        @self.app.event("message")
        async def handle_message(event, say):
            await self._process_message(event)

        @self.app.event("app_mention")
        async def handle_mention(event, say):
            await self._process_message(event)

    async def _process_message(self, event: dict):
        """
        处理 Slack 消息

        Args:
            event: Slack 事件数据
        """
        # 获取消息信息
        channel_id = event.get("channel")
        user_id = event.get("user")
        text = event.get("text", "")
        subtype = event.get("subtype", "")
        bot_id = event.get("bot_id")

        # DEBUG: 打印所有接收到的消息（仅在调试模式）
        # 调试日志：消息基本信息
        logger.debug(
            f"[DEBUG] Message: channel={channel_id}, user={user_id}, subtype={subtype}, bot_id={bot_id}"
        )

        # 忽略没有 channel_id 的消息
        if not channel_id:
            return

        # 忽略某些 subtype 的消息（如 channel_join, channel_leave 等）
        if subtype and subtype not in ["message", "bot_message"]:
            return

        # 忽略没有 user_id 且没有 bot_id 的消息（可能是系统消息）
        if not user_id and not bot_id:
            return

        # 处理 attachments，如果有的话
        attachments = event.get("attachments", [])
        if attachments:
            attachment_texts = []
            for att in attachments:
                title = att.get("title", "").strip()
                att_text = att.get("text", "").strip()
                fallback = att.get("fallback", "").strip()

                parts = []
                if title:
                    parts.append(f"📌 {title}")
                if att_text:
                    parts.append(att_text)
                if fallback and not title and not att_text:
                    parts.append(fallback)

                if parts:
                    attachment_texts.append("\n".join(parts))

            if attachment_texts:
                text = f"{text}\n\n{'─' * 30}\n\n".join(attachment_texts)

        # 忽略没有文本的消息
        if not text:
            return

        # 检查 Channel 是否在映射配置中
        if not self.config.is_channel_mapped(channel_id):
            logger.debug(f"[DEBUG] Channel {channel_id} not in mappings, ignoring")
            return

        # 获取发送者信息
        if bot_id:
            username = await self._get_bot_name(bot_id, event)
        elif user_id:
            username = await self._get_username(user_id)
        else:
            username = "Unknown"

        # 获取对应的 Telegram Chat ID
        telegram_chat_id = self.config.get_telegram_chat_id(channel_id)
        if not telegram_chat_id:
            logger.error(f"No Telegram chat ID for channel {channel_id}")
            return

        # 转发消息
        success = await self.telegram_sender.send_message(
            chat_id=telegram_chat_id, text=text, username=username
        )

        if success:
            # 始终显示成功转发消息
            if self.config.debug:
                logger.info(f"Forwarded: {username}")
            else:
                print(f"[Forwarded] {username}")
        else:
            logger.error(f"Failed to forward message from {username}")

    async def _get_username(self, user_id: str) -> str:
        """
        获取用户显示名称

        Args:
            user_id: Slack 用户 ID

        Returns:
            str: 用户显示名称
        """
        if not user_id:
            return "Unknown"

        try:
            logger.debug(f"[USERNAME] Fetching user info for: {user_id}")

            # 优先获取 display_name，其次 real_name
            result = await self.app.client.users_info(user=user_id)
            user = result.get("user", {})

            # 检查是否是 Bot 用户
            is_bot = user.get("is_bot", False)
            if is_bot:
                bot_name = user.get("name", "Bot")
                logger.debug(f"[USERNAME] User is a bot: {bot_name}")
                return f"🤖 {bot_name}"

            profile = user.get("profile", {})
            display_name = profile.get("display_name", "")
            real_name = profile.get("real_name", "")

            # 备选：用户名（@xxx）
            username = user.get("name", "")

            logger.debug(
                f"[USERNAME] display_name={display_name}, real_name={real_name}, username={username}, is_bot={is_bot}"
            )

            # 优先级：display_name > real_name > username > user_id
            final_name = display_name or real_name or username or user_id
            logger.debug(f"[USERNAME] Final name: {final_name}")

            return final_name

        except Exception as e:
            logger.debug(f"[USERNAME] Failed to get username for {user_id}: {e}")
            # API 调用失败时，尝试从缓存或其他方式获取，或返回简化版 ID
            return f"User-{user_id[:8]}..."

    async def _get_bot_name(self, bot_id: str, event: dict) -> str:
        """获取 Bot 名称 - 只使用 event 中的字段，不调用 API"""
        # 1. 首先从 event 中获取 username（如 Pipedream 会显示 "Pipedream"）
        username = event.get("username", "").strip()
        if username:
            return f"🤖 {username}"

        # 2. 尝试从 attachments 中的 author_name 获取
        attachments = event.get("attachments", [])
        if attachments and isinstance(attachments, list):
            author_name = attachments[0].get("author_name", "").strip()
            if author_name:
                return f"🤖 {author_name}"

        # 3. 尝试从 blocks 中提取
        blocks = event.get("blocks", [])
        if blocks and isinstance(blocks, list):
            for block in blocks:
                if block.get("type") == "header":
                    elements = block.get("text", {})
                    text = elements.get("text", "").strip()
                    if text:
                        return f"🤖 {text}"

        # 4. 从 text 中尝试解析（如 "Pipedream App: message"）
        text = event.get("text", "")
        if text and ":" in text:
            bot_name = text.split(":")[0].strip()
            if bot_name:
                return f"🤖 {bot_name}"

        # 5. 最后返回 Bot ID 的一部分
        return f"🤖 Bot-{bot_id[:8]}" if bot_id else "🤖 Bot"

    async def start(self):
        """启动 Socket Mode 处理器"""
        self._handler = AsyncSocketModeHandler(self.app, self.config.slack_app_token)
        logger.debug("Starting Slack handler...")
        try:
            await self._handler.start_async()
        except asyncio.CancelledError:
            logger.debug("Slack handler received cancel signal")
            raise

    async def stop(self):
        """停止处理器"""
        if self._handler:
            await self._handler.close()
        await self.telegram_sender.close()
        logger.debug("Slack handler stopped")
