from aiogram import Router, F
from aiogram.types import Message

router = Router()


@router.message(F.text == "/id")
async def get_chat_id(message: Message):
    await message.answer(
        f"🆔 Chat ID:\n<code>{message.chat.id}</code>\n\n"
        f"📌 Chat turi: {message.chat.type}\n"
        f"📛 Nomi: {message.chat.title or message.chat.full_name}"
    )
