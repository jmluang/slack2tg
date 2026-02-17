import os
import re
import yaml
from typing import Dict, Optional, Any
from dotenv import load_dotenv

load_dotenv()


class Config:
    """配置管理器"""

    def __init__(self, config_path: str = "config.yaml"):
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        # 递归替换环境变量 ${VAR}
        config = self._replace_env_vars(config)

        # Slack 配置
        self.slack_app_token = config["slack"]["app_token"]
        self.slack_bot_token = config["slack"]["bot_token"]

        # Telegram 配置
        self.telegram_bot_token = config["telegram"]["bot_token"]

        # Channel 映射
        self.channel_mappings: Dict[str, str] = config.get("channel_mappings", {})

        # 调试模式
        debug_env = os.getenv("APP_DEBUG", "false").lower()
        self.debug = debug_env in ("true", "1", "yes", "on")

    def _replace_env_vars(self, obj: Any) -> Any:
        """递归替换对象中的 ${ENV_VAR} 为环境变量值"""
        if isinstance(obj, dict):
            return {
                self._replace_env_vars(k): self._replace_env_vars(v)
                for k, v in obj.items()
            }
        elif isinstance(obj, list):
            return [self._replace_env_vars(item) for item in obj]
        elif isinstance(obj, str):
            # 匹配 ${VAR} 或 ${VAR:-default} 格式
            pattern = r"\$\{([^}]+)\}"

            def replace(match):
                var_expr = match.group(1)
                # 支持 ${VAR:-default} 语法
                if ":-" in var_expr:
                    var_name, default = var_expr.split(":-", 1)
                    return os.getenv(var_name, default)
                else:
                    return os.getenv(var_expr, match.group(0))

            return re.sub(pattern, replace, obj)
        else:
            return obj

    def get_telegram_chat_id(self, slack_channel_id: str) -> Optional[str]:
        """根据 Slack Channel ID 获取对应的 Telegram Chat ID"""
        return self.channel_mappings.get(slack_channel_id)

    def is_channel_mapped(self, slack_channel_id: str) -> bool:
        """检查 Slack Channel 是否在映射配置中"""
        return slack_channel_id in self.channel_mappings
