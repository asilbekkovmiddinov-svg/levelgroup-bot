from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message
import aiohttp

from config import BACKEND_URL

router = Router()


@router.message(CommandStart())
async def start_command(message: Message):
    async with aiohttp.ClientSession() as session:
        try:
            await session.post(
                f"{BACKEND_URL}/user/register",
                json={
                    "telegram_id": message.from_user.id,
                    "first_name": message.from_user.first_name,
                    "username": message.from_user.username or "",
                    "language": "uz"
                }
            )
        except Exception as e:
            print(e)

    await message.answer(
        "👋 Assalomu alaykum!\n\n"
        "LEVEL_GROUP ga xush kelibsiz! 🚀"
    )
