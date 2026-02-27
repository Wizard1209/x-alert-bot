import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher

from bot.config import CONFIG
from bot.handlers import router
from bot.scheduler import run_poll_loop
from bot.storage import UserStorage
from bot.twitter import TwitterClient


async def main() -> None:
    logging.basicConfig(
        level=getattr(logging, CONFIG.log_level),
        stream=sys.stdout,
        format='%(asctime)s | %(levelname)-7s | %(name)s | %(message)s',
    )

    bot = Bot(CONFIG.telegram_bot_token)
    storage = UserStorage()
    client = TwitterClient(bearer_token=CONFIG.x_api_key)

    dp = Dispatcher()
    dp.include_router(router)
    dp['storage'] = storage

    poll_task: asyncio.Task | None = None

    async def on_startup() -> None:
        nonlocal poll_task
        poll_task = asyncio.create_task(
            run_poll_loop(bot, client, storage)
        )

    async def on_shutdown() -> None:
        if poll_task:
            poll_task.cancel()
        await client.close()

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
