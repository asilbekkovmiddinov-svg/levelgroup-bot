from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from config import ADMIN_CHAT_ID

router = Router()


@router.callback_query(F.data.startswith("claim_deposit_"))
async def claim_deposit(callback: CallbackQuery):
    order_id = callback.data.replace("claim_deposit_", "")

    admin_name = (
        f"@{callback.from_user.username}"
        if callback.from_user.username
        else callback.from_user.full_name
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Bajarildi",
                    callback_data=f"approve_deposit_{order_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Bekor qilindi",
                    callback_data=f"reject_deposit_{order_id}"
                )
            ]
        ]
    )

    old_caption = callback.message.caption or ""

    new_caption = (
        old_caption
        + "\n\n━━━━━━━━━━━━━━\n"
        + f"👨‍💼 Qabul qilgan admin: {admin_name}\n"
        + "📌 Status: PROCESSING"
    )

    if callback.message.photo:
        await callback.message.bot.send_photo(
            chat_id=ADMIN_CHAT_ID,
            photo=callback.message.photo[-1].file_id,
            caption=new_caption,
            reply_markup=keyboard
        )
    else:
        await callback.message.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=new_caption,
            reply_markup=keyboard
        )

    await callback.message.delete()

    await callback.answer("✅ Buyurtma sizga biriktirildi.")
