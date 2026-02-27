from aiogram import Router
from aiogram.filters import CommandStart
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
        'Baking Bad feed — monitoring X/Twitter and sending alerts.'
    )
