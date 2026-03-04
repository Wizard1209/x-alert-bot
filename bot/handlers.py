from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from bot.storage import UserStorage

router = Router()


@router.message(CommandStart())
async def cmd_start(
    message: Message, storage: UserStorage
) -> None:
    user = message.from_user
    if not user:
        return

    storage.add_user(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
    )

    await message.answer(
        'Welcome to the Baking Bad alert bot!\n\n'
        'You will receive real-time alerts whenever '
        'Baking Bad and its products post on X/Twitter.\n\n'
        'Use /status to check your registration.'
    )


@router.message(Command('status'))
async def cmd_status(
    message: Message, storage: UserStorage
) -> None:
    user = message.from_user
    if not user:
        return

    if user.id in storage.get_users():
        await message.answer(
            'You are registered and receiving alerts.'
        )
    else:
        storage.add_user(
            user_id=user.id,
            username=user.username,
            first_name=user.first_name,
        )
        await message.answer(
            'You have been re-registered. '
            'You will now receive alerts again.'
        )
