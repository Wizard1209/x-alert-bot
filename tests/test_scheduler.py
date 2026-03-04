"""Tests for bot.scheduler — send_alert, deliver_alerts, poll_step."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram.exceptions import TelegramForbiddenError
from aiogram.utils.formatting import Text

from bot.formatter import TelegramAlert
from bot.scheduler import deliver_alerts, poll_step, send_alert
from bot.twitter import Tweet, TweetType


# ── Helpers ──────────────────────────────────────────────────────


def _make_tweet(tid='100', tweet_type=TweetType.ORIGINAL) -> Tweet:
    return Tweet(
        id=tid,
        text='hello',
        created_at=datetime.now(timezone.utc),
        url=f'https://x.com/user/status/{tid}',
        tweet_type=tweet_type,
        author_username='user',
        author_name='User',
    )


def _make_alert(
    photo_url=None, extra_photos=None, silent=False
) -> TelegramAlert:
    return TelegramAlert(
        text=Text('test alert'),
        photo_url=photo_url,
        extra_photos=extra_photos or [],
        silent=silent,
    )


def _make_users(*ids: int) -> dict[int, dict]:
    return {uid: {'username': f'user{uid}'} for uid in ids}


# ── send_alert ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_send_alert_text_only(mock_bot):
    await send_alert(mock_bot, 111, _make_alert())
    mock_bot.send_message.assert_called_once()
    mock_bot.send_photo.assert_not_called()


@pytest.mark.asyncio
async def test_send_alert_photo(mock_bot):
    alert = _make_alert(photo_url='https://example.com/pic.jpg')
    await send_alert(mock_bot, 111, alert)
    mock_bot.send_photo.assert_called_once()
    assert (
        mock_bot.send_photo.call_args.kwargs['photo']
        == 'https://example.com/pic.jpg'
    )
    mock_bot.send_message.assert_not_called()


@pytest.mark.asyncio
async def test_send_alert_extra_photos(mock_bot):
    alert = _make_alert(
        photo_url='https://example.com/a.jpg',
        extra_photos=[
            'https://example.com/b.jpg',
            'https://example.com/c.jpg',
        ],
    )
    await send_alert(mock_bot, 111, alert)
    assert mock_bot.send_photo.call_count == 3  # 1 main + 2 extras


@pytest.mark.asyncio
async def test_send_alert_silent_flag(mock_bot):
    alert = _make_alert(silent=True)
    await send_alert(mock_bot, 111, alert)
    kwargs = mock_bot.send_message.call_args.kwargs
    assert kwargs['disable_notification'] is True


# ── deliver_alerts ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_deliver_alerts_sends_to_all_users(mock_bot):
    """Each alert is sent to every user."""
    users = _make_users(1, 2, 3)
    alerts = [_make_alert(), _make_alert()]

    blocked = await deliver_alerts(mock_bot, users, alerts)

    assert blocked == []
    # 2 alerts × 3 users = 6 calls
    assert mock_bot.send_message.call_count == 6


@pytest.mark.asyncio
async def test_deliver_alerts_collects_blocked_users(mock_bot):
    """TelegramForbiddenError collects blocked IDs, continues to others."""
    users = _make_users(1, 2, 3)

    def side_effect(*, chat_id, **kw):
        if chat_id == 2:
            raise TelegramForbiddenError(
                method=MagicMock(), message='blocked'
            )

    mock_bot.send_message.side_effect = side_effect

    blocked = await deliver_alerts(
        mock_bot, users, [_make_alert()]
    )

    assert blocked == [2]
    # User 1 and 3 still got their messages
    calls = mock_bot.send_message.call_args_list
    sent_to = [c.kwargs['chat_id'] for c in calls]
    assert 1 in sent_to
    assert 3 in sent_to


@pytest.mark.asyncio
async def test_deliver_alerts_blocked_user_collected_once(mock_bot):
    """Same user blocked across multiple alerts only appears once."""
    users = _make_users(1)
    mock_bot.send_message.side_effect = TelegramForbiddenError(
        method=MagicMock(), message='blocked'
    )

    blocked = await deliver_alerts(
        mock_bot, users, [_make_alert(), _make_alert()]
    )

    assert blocked == [1]  # not [1, 1]


@pytest.mark.asyncio
async def test_deliver_alerts_other_error_continues(mock_bot):
    """Non-forbidden errors are logged but delivery continues."""
    users = _make_users(1, 2)

    call_count = 0

    def side_effect(*, chat_id, **kw):
        nonlocal call_count
        call_count += 1
        if chat_id == 1:
            raise RuntimeError('network error')

    mock_bot.send_message.side_effect = side_effect

    with patch(
        'bot.scheduler.notify_admin', new_callable=AsyncMock
    ) as mock_notify:
        blocked = await deliver_alerts(
            mock_bot, users, [_make_alert()]
        )

    assert blocked == []  # not a forbidden error
    mock_notify.assert_called_once()
    # User 2 still got an attempt
    assert call_count == 2


# ── poll_step ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_poll_step_no_tweets_returns_same_cursor(mock_bot):
    """No tweets → cursor unchanged, no delivery."""
    client = AsyncMock()
    client.poll.return_value = ([], None)
    storage = MagicMock()

    result = await poll_step(mock_bot, client, storage, '50')

    assert result == '50'
    storage.get_users.assert_not_called()
    mock_bot.send_message.assert_not_called()


@pytest.mark.asyncio
async def test_poll_step_delivers_and_advances_cursor(mock_bot):
    """Tweets delivered, cursor advances, save_cursor called."""
    tweets = [_make_tweet('200'), _make_tweet('201')]
    client = AsyncMock()
    client.poll.return_value = (tweets, '201')

    storage = MagicMock()
    storage.get_users.return_value = _make_users(10)

    with (
        patch(
            'bot.scheduler.format_tweet',
            return_value=_make_alert(),
        ),
        patch('bot.scheduler.save_cursor') as mock_save,
    ):
        result = await poll_step(
            mock_bot, client, storage, '100'
        )

    assert result == '201'
    mock_save.assert_called_once_with('201')
    assert mock_bot.send_message.call_count == 2  # 2 alerts × 1 user


@pytest.mark.asyncio
async def test_poll_step_no_users_skips_delivery(mock_bot):
    """No users → skip delivery, but still advance cursor."""
    client = AsyncMock()
    client.poll.return_value = ([_make_tweet()], '100')

    storage = MagicMock()
    storage.get_users.return_value = {}

    with patch('bot.scheduler.save_cursor') as mock_save:
        result = await poll_step(mock_bot, client, storage, '50')

    assert result == '100'
    mock_bot.send_message.assert_not_called()
    mock_save.assert_called_once_with('100')


@pytest.mark.asyncio
async def test_poll_step_removes_blocked_users(mock_bot):
    """Blocked users removed from storage after delivery."""
    client = AsyncMock()
    client.poll.return_value = ([_make_tweet()], '100')

    storage = MagicMock()
    storage.get_users.return_value = _make_users(1, 2)

    def side_effect(*, chat_id, **kw):
        if chat_id == 2:
            raise TelegramForbiddenError(
                method=MagicMock(), message='blocked'
            )

    mock_bot.send_message.side_effect = side_effect

    with (
        patch(
            'bot.scheduler.format_tweet',
            return_value=_make_alert(),
        ),
        patch('bot.scheduler.save_cursor'),
    ):
        await poll_step(mock_bot, client, storage, '50')

    storage.remove_user.assert_called_once_with(2)


@pytest.mark.asyncio
async def test_poll_step_cursor_saved_after_delivery(mock_bot):
    """save_cursor is called AFTER deliver_alerts, not before."""
    call_order = []

    client = AsyncMock()
    client.poll.return_value = ([_make_tweet()], '100')

    storage = MagicMock()
    storage.get_users.return_value = _make_users(10)

    async def fake_send(*, chat_id, **kw):
        call_order.append('send')

    mock_bot.send_message.side_effect = fake_send

    def fake_save(cursor):
        call_order.append('save_cursor')

    with (
        patch(
            'bot.scheduler.format_tweet',
            return_value=_make_alert(),
        ),
        patch(
            'bot.scheduler.save_cursor', side_effect=fake_save
        ),
    ):
        await poll_step(mock_bot, client, storage, '50')

    assert call_order.index('send') < call_order.index(
        'save_cursor'
    )


@pytest.mark.asyncio
async def test_poll_step_reverses_tweet_order(mock_bot):
    """Tweets are delivered oldest-first (reversed from API order)."""
    delivered_ids = []

    # API returns newest first: 300, 200
    tweets = [_make_tweet('300'), _make_tweet('200')]
    client = AsyncMock()
    client.poll.return_value = (tweets, '300')

    storage = MagicMock()
    storage.get_users.return_value = _make_users(10)

    def track_format(tweet):
        delivered_ids.append(tweet.id)
        return _make_alert()

    with (
        patch(
            'bot.scheduler.format_tweet', side_effect=track_format
        ),
        patch('bot.scheduler.save_cursor'),
    ):
        await poll_step(mock_bot, client, storage, '100')

    # Should be reversed: oldest first
    assert delivered_ids == ['200', '300']


@pytest.mark.asyncio
async def test_poll_step_snapshots_users_once(mock_bot):
    """User list is fetched once per poll_step, not per-tweet."""
    tweets = [_make_tweet('1'), _make_tweet('2'), _make_tweet('3')]
    client = AsyncMock()
    client.poll.return_value = (tweets, '3')

    storage = MagicMock()
    storage.get_users.return_value = _make_users(10)

    with (
        patch(
            'bot.scheduler.format_tweet',
            return_value=_make_alert(),
        ),
        patch('bot.scheduler.save_cursor'),
    ):
        await poll_step(mock_bot, client, storage, '0')

    storage.get_users.assert_called_once()
