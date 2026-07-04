from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from keyboards.menu import main_menu

router = Router()

@router.message(CommandStart())
async def start_command(message: Message):
    await message.answer(
        "👋 Assalomu alaykum!\n\n"
        "LEVEL_GROUP ga xush kelibsiz! 🚀",
        reply_markup=main_menu
    )
