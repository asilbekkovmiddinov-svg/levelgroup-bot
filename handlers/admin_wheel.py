from aiogram import Router, F
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

from config import (
    ADMIN_CHAT_ID,
    COMPLETED_ORDERS_CHANNEL_ID,
)

from services.api import (
    approve_wheel_coin_order,
    reject_wheel_coin_order,
)

router = Router()


def wheel_order_keyboard(order_id: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Bajarildi",
                    callback_data=f"wheel_order_done_{order_id}",
                ),
                InlineKeyboardButton(
                    text="❌ Rad etish",
                    callback_data=f"wheel_order_reject_{order_id}",
                ),
            ]
        ]
    )


def format_duration(seconds: int):
    if seconds < 60:
        return f"{seconds} soniya"

    minutes = seconds // 60
    seconds = seconds % 60

    if minutes < 60:
        return f"{minutes} daqiqa {seconds} soniya"

    hours = minutes // 60
    minutes = minutes % 60

    return f"{hours} soat {minutes} daqiqa"
def get_admin_name(user):
    if user.username:
        return f"@{user.username}"
    return user.full_name or str(user.id)


def build_completed_text(data: dict, admin_name: str):
    username = data.get("username") or "username yo‘q"
    coin_amount = int(data.get("coin_amount", 0))

    duration = data.get("duration_seconds") or data.get("seconds") or 0
    duration_text = format_duration(int(duration))

    if coin_amount >= 2000:
        return (
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "👑 NAVBATDAGI JACKPOT G'OLIBI 👑\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🏆 Tabriklaymiz!\n\n"
            f"👤 G'olib:\n@{username}\n\n"
            "💎 Yutuq:\n"
            f"{coin_amount} Coin JACKPOT\n\n"
            "⏱ Bajarilish vaqti:\n"
            f"{duration_text}\n\n"
            "🛡 Bajaruvchi admin:\n"
            f"{admin_name}\n\n"
            "🍀 Balki keyingi JACKPOT g'olibi siz bo'larsiz!\n\n"
            "🔥 LEVEL_GROUP"
        )

    return (
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🎉 WHEEL G'OLIBI\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 G'olib:\n@{username}\n\n"
        "🪙 Yutuq:\n"
        f"{coin_amount} Coin\n\n"
        "⏱ Bajarilish vaqti:\n"
        f"{duration_text}\n\n"
        "🛡 Bajaruvchi admin:\n"
        f"{admin_name}\n\n"
        "🎊 Tabriklaymiz!\n\n"
        "🔥 LEVEL_GROUP"
    )


async def safe_send(bot, chat_id, text):
    try:
        await bot.send_message(chat_id=chat_id, text=text)
        return True
    except Exception:
        return False
@router.callback_query(F.data.startswith("wheel_order_done_"))
async def approve_wheel(callback: CallbackQuery):
    order_id = int(callback.data.replace("wheel_order_done_", ""))

    result = await approve_wheel_coin_order(
        order_id=order_id,
        admin_id=callback.from_user.id,
    )

    if not result.get("success"):
        await callback.answer(
            result.get("message", "Xatolik"),
            show_alert=True,
        )
        return

    data = result["data"]

    admin_name = get_admin_name(callback.from_user)

    completed_text = build_completed_text(
        data,
        admin_name,
    )

    await safe_send(
        callback.bot,
        COMPLETED_ORDERS_CHANNEL_ID,
        completed_text,
    )

    try:
        await callback.bot.send_message(
            chat_id=data["telegram_id"],
            text=(
                "🎉 Tabriklaymiz!\n\n"
                f"🪙 {data['coin_amount']} Coin hisobingizga muvaffaqiyatli tashlab berildi.\n\n"
                "🔥 LEVEL_GROUP"
            ),
        )
    except Exception:
        pass

    await callback.message.edit_reply_markup()

    await callback.answer("✅ Buyurtma bajarildi.")


@router.callback_query(F.data.startswith("wheel_order_reject_"))
async def reject_wheel(callback: CallbackQuery):
    order_id = int(callback.data.replace("wheel_order_reject_", ""))

    result = await reject_wheel_coin_order(
        order_id=order_id,
        admin_id=callback.from_user.id,
    )

    if not result.get("success"):
        await callback.answer(
            result.get("message", "Xatolik"),
            show_alert=True,
        )
        return

    data = result["data"]

    try:
        await callback.bot.send_message(
            chat_id=data["telegram_id"],
            text=(
                "❌ Wheel Coin buyurtmangiz admin tomonidan rad etildi.\n\n"
                "Qo'shimcha ma'lumot uchun admin bilan bog'laning."
            ),
        )
    except Exception:
        pass

    await callback.message.edit_reply_markup()

    await callback.answer("❌ Buyurtma rad etildi.")
