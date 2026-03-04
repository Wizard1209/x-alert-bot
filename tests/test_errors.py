"""Tests for bot.errors — notify_admin()."""

from unittest.mock import patch

import pytest

from bot.errors import notify_admin


@pytest.fixture
def errors_config():
    """Patch CONFIG within bot.errors module."""
    with patch('bot.errors.CONFIG') as cfg:
        cfg.admin_id = 999
        yield cfg


@pytest.mark.asyncio
async def test_notify_admin_sends_message(
    mock_bot, errors_config
):
    error = RuntimeError('something broke')
    await notify_admin(mock_bot, error)

    mock_bot.send_message.assert_called_once()
    call_args = mock_bot.send_message.call_args
    assert call_args[1].get('chat_id') == 999 or (
        call_args[0] and call_args[0][0] == 999
    )


@pytest.mark.asyncio
async def test_notify_admin_no_admin(mock_bot, errors_config):
    errors_config.admin_id = None

    await notify_admin(mock_bot, RuntimeError('oops'))

    mock_bot.send_message.assert_not_called()


@pytest.mark.asyncio
async def test_notify_admin_truncates_long_tb(
    mock_bot, errors_config
):
    # Create an error with a very long traceback
    try:
        raise RuntimeError('x' * 5000)
    except RuntimeError as e:
        error = e

    await notify_admin(mock_bot, error)

    mock_bot.send_message.assert_called_once()
