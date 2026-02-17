import html
import logging
from typing import Optional
from telegram import Bot
from telegram.constants import ParseMode

logger = logging.getLogger(__name__)


class TelegramSender:
    """Telegram 消息发送器"""

    def __init__(self, bot_token: str):
        self.bot = Bot(token=bot_token)

    async def send_message(
        self, chat_id: str, text: str, username: Optional[str] = None
    ) -> bool:
        """发送消息到 Telegram"""
        try:
            # HTML 转义用户名和文本，避免特殊字符导致解析错误
            if username:
                escaped_username = html.escape(username)
                escaped_text = html.escape(text)
                formatted_text = f"<b>{escaped_username}</b>:\n{escaped_text}"
            else:
                formatted_text = html.escape(text)

            # 处理长消息（Telegram 限制 4096 字符）
            if len(formatted_text) > 4000:
                formatted_text = formatted_text[:3997] + "..."

            await self.bot.send_message(
                chat_id=chat_id, text=formatted_text, parse_mode=ParseMode.HTML
            )
            return True

        except Exception as e:
            logger.error(f"TG send failed: {e}")
            return False

    async def close(self):
        """关闭 Bot 连接"""
        await self.bot.session.close()
