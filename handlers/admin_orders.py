from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from config import ADMIN_CHAT_ID
from services.api import claim_deposit, approve_deposit, reject_deposit

router = Router()


@router.callback_query(F.data.startswith("claim_deposit_"))
async def claim_deposit_handler(callback: CallbackQuery):
    deposit_id = int(callback.data.replace("claim_deposit_", ""))

    result = await claim_deposit(
        deposit_id=deposit_id,
        admin_id=callback.from_user.id
    )

    if result.get("message") == "Deposit already claimed":
        await callback.answer(
            "❌ Bu depozit allaqachon boshqa admin tomonidan qabul qilingan.",
            show_alert=True
        )
        return

    if result.get("message") != "Deposit claimed":
        await callback.answer("❌ Xatolik yuz berdi.", show_alert=True)
        return

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
                    callback_data=f"approve_deposit_{deposit_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Bekor qilindi",
                    callback_data=f"reject_deposit_{deposit_id}"
                )
            ]
        ]
    )

    old_caption = callback.message.caption or ""

    new_caption = (
        old_caption
        + "\n\n━━━━━━━━━━━━━━\n"
        + f"👨‍💼 Qabul qilgan admin: {admin_name}\n"
        + "📌 Status: CLAIMED"
    )

    await callback.message.bot.send_photo(
        chat_id=ADMIN_CHAT_ID,
        photo=callback.message.photo[-1].file_id,
        caption=new_caption,
        reply_markup=keyboard
    )

    await callback.message.delete()
    await callback.answer("✅ Depozit sizga biriktirildi.")


@router.callback_query(F.data.startswith("approve_deposit_"))
async def approve_deposit_handler(callback: CallbackQuery):
    deposit_id = int(callback.data.replace("approve_deposit_", ""))

    result = await approve_deposit(
        deposit_id=deposit_id,
        admin_id=callback.from_user.id
    )

    if result.get("message") != "Deposit approved":
        await callback.answer("❌ Tasdiqlashda xatolik.", show_alert=True)
        return

    caption = callback.message.caption or ""
    caption = caption.replace("📌 Status: CLAIMED", "🟢 Status: COMPLETED")

    await callback.message.edit_caption(
        caption=caption,
        reply_markup=None
    )

    await callback.answer("✅ Depozit bajarildi.")


@router.callback_query(F.data.startswith("reject_deposit_"))
async def reject_deposit_handler(callback: CallbackQuery):
    deposit_id = int(callback.data.replace("reject_deposit_", ""))

    result = await reject_deposit(
        deposit_id=deposit_id,
        admin_id=callback.from_user.id
    )

    if result.get("message") != "Deposit rejected":
        await callback.answer("❌ Rad etishda xatolik.", show_alert=True)
        return

    caption = callback.message.caption or ""
    caption = caption.replace("📌 Status: CLAIMED", "🔴 Status: REJECTED")

    await callback.message.edit_caption(
        caption=caption,
        reply_markup=None
    )

    await callback.answer("❌ Depozit rad etildi.")
