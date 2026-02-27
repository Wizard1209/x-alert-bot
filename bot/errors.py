"""Global error handler — sends tracebacks to admin."""

import contextlib
import traceback

from aiogram import Bot, Dispatcher
from aiogram.types import ErrorEvent
from aiogram.types.error_event import ErrorEvent  # noqa: F811
from aiogram.utils.formatting import Bold, Pre, Text, as_list

from bot.config import CONFIG


async def global_error_handler(
    event: ErrorEvent, bot: Bot
) -> bool:
    error = event.exception
    error_class = type(error).__name__

    if not CONFIG.admin_id:
        return True

    tb = ''.join(
        traceback.format_exception(
            type(error), error, error.__traceback__
        )
    )
    if len(tb) > 3000:
        tb = tb[:1500] + '\n...\n' + tb[-1000:]

    content = as_list(
        Text('🚨 '),
        Bold('Bot Error'),
        Text('\n'),
        Bold('Type: '),
        Text(error_class),
        Text('\n'),
        Bold('Error: '),
        Text(str(error)[:300]),
        Text('\n\n'),
        Pre(tb),
    )

    with contextlib.suppress(Exception):
        await bot.send_message(
            CONFIG.admin_id, **content.as_kwargs()
        )

    return True


def setup_error_handler(dp: Dispatcher) -> None:
    dp.errors.register(global_error_handler)
