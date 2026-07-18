from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from datetime import datetime
from zoneinfo import ZoneInfo

from config import ADMIN_CHAT_ID, ADMIN_USER_IDS, COMPLETED_ORDERS_CHANNEL_ID
from services.api import claim_shop_order, complete_shop_order, reject_shop_order


router = Router()
TASHKENT = ZoneInfo("Asia/Tashkent")


def is_admin(user_id: int) -> bool:
    value = int(user_id)
    return value in ADMIN_USER_IDS or (bool(ADMIN_CHAT_ID) and value == int(ADMIN_CHAT_ID))


def line_value(text: str, label: str, default: str = "—") -> str:
    for line in str(text or "").splitlines():
        if line.startswith(label):
            return line[len(label):].strip()
    return default


def action_keyboard(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="✅ Buyurtma bajarildi",
            callback_data=f"coinshop:{order_id}:COMPLETE",
        ),
        InlineKeyboardButton(
            text="❌ Buyurtma rad etildi",
            callback_data=f"coinshop:{order_id}:REJECT",
        ),
    ]])


def tashkent_time(value) -> str:
    if not value:
        return "—"
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(TASHKENT).strftime("%d.%m.%Y %H:%M:%S")
    except ValueError:
        return str(value)


@router.callback_query(F.data.startswith("coinshop:"))
async def shop_order_action(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return await callback.answer("Ruxsat yo‘q", show_alert=True)

    _, raw_id, action = callback.data.split(":")
    order_id = int(raw_id)
    if action == "CLAIM":
        result = await claim_shop_order(order_id, callback.from_user.id)
        if not result.get("success"):
            return await callback.answer(result.get("detail") or result.get("message") or "Xatolik", show_alert=True)
        data = result["data"]
        source = callback.message.text or callback.message.caption or ""
        username = line_value(source, "👤 Username:")
        await callback.bot.send_message(
            ADMIN_CHAT_ID,
            "🪙 Qabul qilingan Coin buyurtma\n\n"
            f"🔢 Tartib raqami: {data['id']}\n"
            f"🔐 Order raqami: {data['order_number']}\n"
            f"👤 Username: {username}\n"
            f"📦 Coin paketi: {data['product_title']}\n"
            f"🪙 Miqdori: {data['coins_amount']} Coin\n"
            f"🛡 Operator: @{callback.from_user.username or callback.from_user.id}",
            reply_markup=action_keyboard(order_id),
        )
        await callback.message.delete()
        return await callback.answer("Buyurtma sizga biriktirildi")

    if action not in {"COMPLETE", "REJECT"}:
        return await callback.answer("Noto‘g‘ri amal", show_alert=True)
    operation = complete_shop_order if action == "COMPLETE" else reject_shop_order
    result = await operation(order_id, callback.from_user.id)
    if not result.get("success"):
        return await callback.answer(result.get("detail") or result.get("message") or "Xatolik", show_alert=True)
    data = result["data"]
    source = callback.message.text or callback.message.caption or ""
    username = line_value(source, "👤 Username:")
    operator = f"@{callback.from_user.username}" if callback.from_user.username else callback.from_user.full_name
    finished_at = data.get("completed_at") if data["status"] == "COMPLETED" else data.get("rejected_at")
    await callback.bot.send_message(
        COMPLETED_ORDERS_CHANNEL_ID,
        f"{'✅' if data['status'] == 'COMPLETED' else '❌'} Coin buyurtma yakunlandi\n\n"
        f"🔢 Tartib raqami: {data['id']}\n"
        f"👤 Username: {username}\n"
        f"📦 Coin paketi: {data['product_title']}\n"
        f"🪙 Miqdori: {data['coins_amount']} Coin\n"
        f"🛡 Operator: {operator}\n"
        f"📌 Holati: {data['status']}\n"
        f"🕒 Yakunlangan vaqt: {tashkent_time(finished_at)}",
    )
    await callback.message.delete()
    await callback.answer("Buyurtma yakunlandi")
