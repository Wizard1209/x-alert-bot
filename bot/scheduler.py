"""Poll scheduler: fetches tweets and delivers alerts to Telegram users.

Three-layer decomposition:
  1. run_poll_loop  — orchestrator (infinite loop + sleep)
  2. poll_step      — single poll-then-deliver iteration
  3. deliver_alerts — send formatted alerts to all users
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError

from bot.config import CONFIG
from bot.errors import notify_admin
from bot.formatter import TelegramAlert, format_tweet
from bot.storage import UserStorage, load_cursor, save_cursor
from bot.twitter import TwitterClient

logger = logging.getLogger(__name__)

DELIVERY_PAUSE = 0.15  # seconds between alerts (Telegram rate limit)


# ── Layer 3: send one alert to one chat ──────────────────────────


async def send_alert(
    bot: Bot, chat_id: int, alert: TelegramAlert
) -> None:
    """Send a single TelegramAlert to a chat."""
    silent = alert.silent
    if alert.photo_url:
        await bot.send_photo(
            chat_id=chat_id,
            photo=alert.photo_url,
            disable_notification=silent,
            **alert.text.as_caption_kwargs(),
        )
    else:
        await bot.send_message(
            chat_id=chat_id,
            disable_notification=silent,
            **alert.text.as_kwargs(),
        )

    for url in alert.extra_photos:
        await bot.send_photo(
            chat_id=chat_id,
            photo=url,
            disable_notification=silent,
        )


# ── Layer 3: deliver alerts to all users ─────────────────────────


async def deliver_alerts(
    bot: Bot,
    users: dict[int, dict[str, Any]],
    alerts: list[TelegramAlert],
) -> list[int]:
    """Send each alert to every user. Returns list of blocked user IDs."""
    blocked: list[int] = []

    for alert in alerts:
        for chat_id in users:
            try:
                await send_alert(bot, chat_id, alert)
            except TelegramForbiddenError:
                if chat_id not in blocked:
                    blocked.append(chat_id)
                    logger.warning(
                        'User %d blocked the bot', chat_id
                    )
            except Exception as exc:
                logger.error(
                    'Failed to send alert to %d: %s', chat_id, exc
                )
                await notify_admin(bot, exc)

        # Brief pause between alerts to respect Telegram rate limits
        await asyncio.sleep(DELIVERY_PAUSE)

    return blocked


# ── Layer 2: single poll iteration ───────────────────────────────


async def poll_step(
    bot: Bot,
    client: TwitterClient,
    storage: UserStorage,
    cursor: str | None,
    last_polled: datetime | None = None,
) -> str | None:
    """Run one poll-then-deliver cycle. Returns the new cursor."""
    tweets, new_cursor = await client.poll(cursor, last_polled)

    if not tweets:
        return cursor  # unchanged

    # X API returns newest first — deliver oldest first
    tweets.reverse()

    # Snapshot user list once for the whole delivery
    users = storage.get_users()
    if not users:
        logger.warning('No registered users — skipping delivery')
        save_cursor(new_cursor)
        return new_cursor

    alerts = [format_tweet(t) for t in tweets]

    blocked_ids = await deliver_alerts(bot, users, alerts)

    # Persist cursor after all deliveries complete
    save_cursor(new_cursor)

    # Remove blocked users after full delivery pass
    for uid in blocked_ids:
        storage.remove_user(uid)

    return new_cursor


# ── Layer 1: orchestrator ────────────────────────────────────────


async def run_poll_loop(
    bot: Bot,
    client: TwitterClient,
    storage: UserStorage,
) -> None:
    """Top-level infinite loop. Polls, delivers, sleeps, repeats."""
    cursor = load_cursor(max_age_minutes=CONFIG.poll_interval)
    logger.info(
        'Poll loop started (interval=%dm, cursor=%s)',
        CONFIG.poll_interval,
        cursor,
    )

    last_polled: datetime | None = None

    while True:
        try:
            cursor = await poll_step(
                bot, client, storage, cursor, last_polled
            )
        except Exception as exc:
            logger.exception('Poll iteration failed')
            await notify_admin(bot, exc)
            # Keep the same cursor — will retry next iteration

        last_polled = datetime.now(timezone.utc)
        await asyncio.sleep(CONFIG.poll_interval * 60)
