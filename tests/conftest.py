"""Shared test fixtures."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from bot.twitter import TwitterClient


@pytest.fixture(autouse=True)
def mock_config():
    """Patch CONFIG with test-safe values for all tests."""
    with patch('bot.config.CONFIG') as cfg:
        cfg.watch_users = ['alice', 'bob']
        cfg.poll_interval = 1
        cfg.admin_id = 999
        cfg.x_api_key = 'test-bearer-token'
        cfg.telegram_bot_token = 'test-bot-token'
        cfg.log_level = 'DEBUG'
        yield cfg


@pytest.fixture
def mock_bot():
    """AsyncMock aiogram Bot with send_message/send_photo."""
    from aiogram import Bot

    bot = AsyncMock(spec=Bot)
    bot.send_message = AsyncMock()
    bot.send_photo = AsyncMock()
    return bot


@pytest.fixture
def tmp_storage(tmp_path):
    """Patch storage paths to tmp_path, return fresh UserStorage."""
    data_dir = tmp_path / 'data'
    data_dir.mkdir()
    users_file = data_dir / 'users.json'
    cursor_file = data_dir / 'cursor.json'

    with (
        patch('bot.storage.DATA_DIR', data_dir),
        patch('bot.storage.USERS_FILE', users_file),
        patch('bot.storage.CURSOR_FILE', cursor_file),
    ):
        from bot.storage import UserStorage

        yield UserStorage()


@pytest.fixture
def make_twitter_client():
    """Factory: create TwitterClient with mock transport returning given JSON."""

    def _factory(response_json: dict) -> TwitterClient:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json=response_json,
                request=request,
            )

        transport = httpx.MockTransport(handler)
        client = TwitterClient(bearer_token='test-bearer')
        # Replace the internal client with one using mock transport
        client._client = httpx.AsyncClient(
            base_url='https://api.x.com/2',
            headers={'Authorization': 'Bearer test-bearer'},
            transport=transport,
        )
        return client

    return _factory
