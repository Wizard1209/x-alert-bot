"""Poll scheduler: fetches tweets and delivers alerts to Telegram users."""

import asyncio
import logging

from aiogram import Bot

from bot.config import CONFIG
from bot.formatter import TelegramAlert, format_tweet
from bot.storage import UserStorage, load_cursor, save_cursor
from bot.twitter import TwitterClient

logger = logging.getLogger(__name__)


async def send_alert(bot: Bot, chat_id: int, alert: TelegramAlert) -> None:
    """Send a single TelegramAlert to a chat."""
    if alert.photo_url:
        await bot.send_photo(
            chat_id=chat_id,
            photo=alert.photo_url,
            **alert.text.as_caption_kwargs(),
        )
    else:
        await bot.send_message(
            chat_id=chat_id,
            **alert.text.as_kwargs(),
        )

    # Extra photos as separate messages
    for url in alert.extra_photos:
        await bot.send_photo(chat_id=chat_id, photo=url)


async def run_poll_loop(
    bot: Bot,
    client: TwitterClient,
    storage: UserStorage,
) -> None:
    """Main poll loop — runs forever, polling every poll_interval."""
    cursor = load_cursor()
    interval = CONFIG.poll_interval * 60  # seconds

    logger.info(
        'Scheduler started: interval=%dm, cursor=%s',
        CONFIG.poll_interval,
        cursor,
    )

    while True:
        try:
            tweets, new_cursor = await client.poll(cursor)

            if tweets:
                users = storage.get_users()
                # Send oldest first (API returns newest first)
                for tweet in reversed(tweets):
                    alert = format_tweet(tweet)
                    for chat_id in users:
                        try:
                            await send_alert(bot, chat_id, alert)
                        except Exception:
                            logger.exception(
                                'Failed to send to %s', chat_id
                            )
                        await asyncio.sleep(0.15)

                # Advance cursor only after successful delivery
                if new_cursor:
                    cursor = new_cursor
                    save_cursor(cursor)

        except Exception:
            logger.exception('Poll loop error')

        await asyncio.sleep(interval)
