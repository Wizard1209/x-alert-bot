import json
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        extra='ignore',
    )

    telegram_bot_token: str
    x_api_key: str = ''

    # X usernames to monitor (JSON array, no @ prefix)
    watch_users: list[str] = []
    # Poll interval in minutes
    poll_interval: int = 30
    # Admin Telegram ID for error notifications
    admin_id: int | None = None

    log_level: Literal['DEBUG', 'INFO', 'WARNING', 'ERROR'] = 'INFO'

    @field_validator('watch_users', mode='before')
    @classmethod
    def parse_watch_users(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return json.loads(v)
        return v


CONFIG = Config()
