import asyncio
import logging
import os
import sys
import ssl
import certifi
import threading
from pathlib import Path

# 修复 macOS SSL 证书问题
ssl._create_default_https_context = ssl._create_unverified_context
os.environ["SSL_CERT_FILE"] = certifi.where()
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()

# 添加 src 目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent))

from src.config import Config
from src.slack_handler import SlackHandler

# 先加载配置获取 debug 模式
temp_config = Config()

if temp_config.debug:
    # 调试模式：显示所有日志
    logging.basicConfig(
        level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
    )
else:
    # 正常模式：只显示 WARNING 级别（不包括 INFO）
    # 我们的代码会直接打印到 stdout 而不是使用 logging
    logging.basicConfig(
        level=logging.WARNING, format="%(asctime)s - %(levelname)s - %(message)s"
    )

# 抑制所有第三方库的日志
for lib in ["slack_bolt", "slack_sdk", "telegram", "aiohttp", "httpx", "dotenv"]:
    logging.getLogger(lib).setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


class SlackToTelegramBot:
    """Slack 到 Telegram 转发 Bot"""

    def __init__(self):
        self.config = temp_config
        self.handler = SlackHandler(self.config)

    async def run(self):
        """运行 Bot"""
        try:
            if self.config.debug:
                logger.info(
                    f"Starting - monitoring {len(self.config.channel_mappings)} channel(s)"
                )

            # 启动 Slack 处理器（这会一直运行直到出错）
            await self.handler.start()

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error: {e}")
            raise
        finally:
            await self.handler.stop()


def run_in_thread(bot):
    """在单独线程中运行 bot"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(bot.run())
    except Exception as e:
        logger.error(f"Bot error: {e}")
    finally:
        loop.close()


def main():
    """主入口函数"""
    if temp_config.debug:
        print("[DEBUG] Debug mode enabled")

    print(f"Started - monitoring {len(temp_config.channel_mappings)} channel(s)")

    bot = SlackToTelegramBot()

    # 在后台线程中运行 bot
    bot_thread = threading.Thread(target=run_in_thread, args=(bot,), daemon=True)
    bot_thread.start()

    if temp_config.debug:
        logger.info("Press Ctrl+C to stop")

    try:
        # 主线程等待，可以通过 Ctrl+C 中断
        while bot_thread.is_alive():
            bot_thread.join(timeout=1)
    except KeyboardInterrupt:
        if temp_config.debug:
            logger.info("Stopping bot...")
    finally:
        if temp_config.debug:
            logger.info("Bot stopped")
        sys.exit(0)


if __name__ == "__main__":
    main()
