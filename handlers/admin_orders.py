from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from config import ADMIN_CHAT_ID, ADMIN_LOGS_CHANNEL_ID, COMPLETED_ORDERS_CHANNEL_ID
from services.api import (
    claim_deposit,
    claim_withdraw,
    approve_deposit,
    reject_deposit,
    approve_withdraw,
    reject_withdraw,
)

router = Router()
active_actions = set()


def format_seconds(seconds):
    if not seconds:
        return "0 soniya"

    minutes = seconds // 60
    sec = seconds % 60

    if minutes > 0:
        return f"{minutes} daqiqa {sec} soniya"

    return f"{sec} soniya"


def get_admin_name(user):
    if user.username:
        return f"@{user.username}"
    return user.full_name


def get_line_value(text: str, label: str, default: str = "Nomaʼlum"):
    for line in text.splitlines():
        if line.startswith(label):
            return line.replace(label, "").strip()
    return default


async def notify_user(bot, telegram_id, text):
    try:
        await bot.send_message(chat_id=telegram_id, text=text)
        return True
    except Exception:
        return False


async def begin_action(callback: CallbackQuery, action: str, order_id: int):
    key = f"{action}:{order_id}"
    if key in active_actions:
        await callback.answer("⏳ Amal allaqachon bajarilmoqda.", show_alert=True)
        return None
    active_actions.add(key)
    return key


def withdraw_is_claimed(callback: CallbackQuery):
    return "📌 Status: CLAIMED" in (callback.message.text or "")


@router.callback_query(F.data.startswith("claim_deposit_"))
async def claim_deposit_handler(callback: CallbackQuery):
    deposit_id = int(callback.data.replace("claim_deposit_", ""))
    action_key = await begin_action(callback, "claim_deposit", deposit_id)
    if not action_key:
        return

    try:
        result = await claim_deposit(
            deposit_id=deposit_id,
            admin_id=callback.from_user.id,
        )
    finally:
        active_actions.discard(action_key)

    if result.get("status_code") == 409:
        await callback.answer(
            "❌ Bu depozit allaqachon qabul qilingan yoki holati o‘zgargan.",
            show_alert=True,
        )
        return

    if result.get("message") != "Deposit claimed":
        await callback.answer(
            f"❌ Xatolik: {result.get('message', 'Nomaʼlum')}",
            show_alert=True,
        )
        return

    admin_name = get_admin_name(callback.from_user)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Bajarildi",
                    callback_data=f"approve_deposit_{deposit_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Bekor qilindi",
                    callback_data=f"reject_deposit_{deposit_id}",
                )
            ],
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
        reply_markup=keyboard,
    )

    await callback.message.delete()
    await callback.answer("✅ Depozit sizga biriktirildi.")
@router.callback_query(F.data.startswith("approve_deposit_"))
async def approve_deposit_handler(callback: CallbackQuery):
    deposit_id = int(callback.data.replace("approve_deposit_", ""))
    action_key = await begin_action(callback, "approve_deposit", deposit_id)
    if not action_key:
        return

    try:
        result = await approve_deposit(
            deposit_id=deposit_id,
            admin_id=callback.from_user.id,
        )
    finally:
        active_actions.discard(action_key)

    if result.get("message") != "Deposit approved":
        await callback.answer(
            f"❌ Xatolik: {result.get('message', 'Nomaʼlum')}",
            show_alert=True,
        )
        return

    admin_name = get_admin_name(callback.from_user)
    processing_time = format_seconds(result.get("processing_seconds"))

    telegram_id = result.get("telegram_id")
    username = result.get("username", "Nomaʼlum")
    amount = int(result.get("amount", 0))

    caption = callback.message.caption or ""
    caption = caption.replace("📌 Status: CLAIMED", "🟢 Status: APPROVED")

    await callback.message.edit_caption(caption=caption, reply_markup=None)

    user_notified = await notify_user(
        bot=callback.message.bot,
        telegram_id=telegram_id,
        text=(
            "✅ Hisobingiz to‘ldirildi!\n\n"
            f"🆔 Buyurtma: #{deposit_id}\n"
            f"💵 Summa: {amount:,} so‘m\n\n"
            "Balansingizga mablag‘ qo‘shildi.\n\n"
            "🔥 LEVEL_GROUP"
        ),
    )

    await callback.message.bot.send_message(
        chat_id=ADMIN_LOGS_CHANNEL_ID,
        text=(
            "✅ DEPOZIT BAJARILDI\n\n"
            f"🆔 Buyurtma: #{deposit_id}\n"
            f"👤 Mijoz: {username}\n"
            f"🆔 Telegram ID: {telegram_id}\n\n"
            "🎮 Xizmat: UZS to'ldirish\n"
            f"💵 Summa: {amount:,} so'm\n\n"
            f"👨‍💼 Admin: {admin_name}\n"
            f"⏳ Bajarish vaqti: {processing_time}\n"
            f"📩 Mijozga xabar: {'Yuborildi' if user_notified else 'Yuborilmadi'}"
        ),
    )

    await callback.message.bot.send_message(
        chat_id=COMPLETED_ORDERS_CHANNEL_ID,
        text=(
            "✅ BUYURTMA BAJARILDI\n\n"
            f"🆔 Buyurtma: #{deposit_id}\n"
            f"👤 Buyurtmachi: {username}\n\n"
            "🎮 Xizmat: UZS to'ldirish\n"
            f"💵 Summa: {amount:,} so'm\n\n"
            f"👨‍💼 Admin: {admin_name}\n"
            f"⏳ Bajarish vaqti: {processing_time}\n\n"
            "🔥 LEVEL_GROUP"
        ),
    )

    await callback.answer("✅ Depozit bajarildi.")


@router.callback_query(F.data.startswith("reject_deposit_"))
async def reject_deposit_handler(callback: CallbackQuery):
    deposit_id = int(callback.data.replace("reject_deposit_", ""))
    action_key = await begin_action(callback, "reject_deposit", deposit_id)
    if not action_key:
        return

    try:
        result = await reject_deposit(
            deposit_id=deposit_id,
            admin_id=callback.from_user.id,
        )
    finally:
        active_actions.discard(action_key)

    if result.get("message") != "Deposit rejected":
        await callback.answer(
            f"❌ Xatolik: {result.get('message', 'Nomaʼlum')}",
            show_alert=True,
        )
        return

    admin_name = get_admin_name(callback.from_user)
    processing_time = format_seconds(result.get("processing_seconds"))

    telegram_id = result.get("telegram_id")
    username = result.get("username", "Nomaʼlum")
    amount = int(result.get("amount", 0))
    reason = result.get("reason", "Admin rad etdi")

    caption = callback.message.caption or ""
    caption = caption.replace("📌 Status: CLAIMED", "🔴 Status: REJECTED")

    await callback.message.edit_caption(caption=caption, reply_markup=None)

    user_notified = await notify_user(
        bot=callback.message.bot,
        telegram_id=telegram_id,
        text=(
            "❌ Hisob to‘ldirish so‘rovingiz rad etildi.\n\n"
            f"🆔 Buyurtma: #{deposit_id}\n"
            f"💵 Summa: {amount:,} so‘m\n"
            f"📌 Sabab: {reason}\n\n"
            "Iltimos, maʼlumotlarni tekshirib qayta urinib ko‘ring.\n\n"
            "🔥 LEVEL_GROUP"
        ),
    )

    await callback.message.bot.send_message(
        chat_id=ADMIN_LOGS_CHANNEL_ID,
        text=(
            "❌ DEPOZIT RAD ETILDI\n\n"
            f"🆔 Buyurtma: #{deposit_id}\n"
            f"👤 Mijoz: {username}\n"
            f"🆔 Telegram ID: {telegram_id}\n\n"
            f"💵 Summa: {amount:,} so'm\n"
            f"👨‍💼 Admin: {admin_name}\n"
            f"📌 Sabab: {reason}\n"
            f"⌛️ Ko‘rib chiqish vaqti: {processing_time}\n"
            f"📩 Mijozga xabar: {'Yuborildi' if user_notified else 'Yuborilmadi'}"
        ),
    )

    await callback.answer("❌ Depozit rad etildi.")
@router.callback_query(F.data.startswith("claim_withdraw_"))
async def claim_withdraw_handler(callback: CallbackQuery):
    withdraw_id = int(callback.data.replace("claim_withdraw_", ""))
    action_key = await begin_action(callback, "claim_withdraw", withdraw_id)
    if not action_key:
        return

    try:
        result = await claim_withdraw(
            withdraw_id=withdraw_id,
            admin_id=callback.from_user.id,
        )
    finally:
        active_actions.discard(action_key)

    if result.get("status_code") == 409:
        await callback.answer(
            "❌ Bu withdraw allaqachon qabul qilingan yoki holati o‘zgargan.",
            show_alert=True,
        )
        return

    if result.get("message") != "Withdraw claimed":
        await callback.answer(
            f"❌ Xatolik: {result.get('message', 'Nomaʼlum')}",
            show_alert=True,
        )
        return

    admin_name = get_admin_name(callback.from_user)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Tasdiqlash",
                    callback_data=f"approve_withdraw_{withdraw_id}",
                ),
                InlineKeyboardButton(
                    text="❌ Rad etish",
                    callback_data=f"reject_withdraw_{withdraw_id}",
                ),
            ]
        ]
    )

    old_text = callback.message.text or ""
    new_text = (
        old_text
        + "\n\n━━━━━━━━━━━━━━\n"
        + f"👨‍💼 Qabul qilgan admin: {admin_name}\n"
        + "📌 Status: CLAIMED"
    )

    await callback.message.bot.send_message(
        chat_id=ADMIN_CHAT_ID,
        text=new_text,
        reply_markup=keyboard,
    )

    await callback.message.delete()
    await callback.answer("✅ Withdraw sizga biriktirildi.")


@router.callback_query(F.data.startswith("approve_withdraw_"))
async def approve_withdraw_handler(callback: CallbackQuery):
    withdraw_id = int(callback.data.replace("approve_withdraw_", ""))

    old_text = callback.message.text or ""
    if not withdraw_is_claimed(callback):
        await callback.answer("❌ Avval withdraw so‘rovini claim qiling.", show_alert=True)
        return
    action_key = await begin_action(callback, "approve_withdraw", withdraw_id)
    if not action_key:
        return
    username = get_line_value(old_text, "👤 Mijoz:")

    try:
        result = await approve_withdraw(
            withdraw_id=withdraw_id,
            admin_id=callback.from_user.id,
        )
    finally:
        active_actions.discard(action_key)

    if result.get("status_code") == 409:
        await callback.answer(
            "❌ Bu withdraw holati o‘zgargan yoki boshqa adminga biriktirilgan.",
            show_alert=True,
        )
        return

    if result.get("message") != "Withdraw tasdiqlandi":
        await callback.answer(
            f"❌ Xatolik: {result.get('message', 'Nomaʼlum')}",
            show_alert=True,
        )
        return

    admin_name = get_admin_name(callback.from_user)
    processing_time = format_seconds(result.get("processing_seconds"))

    telegram_id = result.get("telegram_id")
    amount = int(result.get("amount", 0))
    bank_name = result.get("bank_name", "Nomaʼlum")
    card_number = result.get("card_number", "Nomaʼlum")
    card_holder = result.get("card_holder", "Nomaʼlum")

    await callback.message.edit_text(
        text=old_text.replace("📌 Status: CLAIMED", "🟢 Status: APPROVED"),
        reply_markup=None,
    )

    user_notified = await notify_user(
        bot=callback.message.bot,
        telegram_id=telegram_id,
        text=(
            "✅ Pul yechish so‘rovingiz tasdiqlandi!\n\n"
            f"🆔 Buyurtma: #{withdraw_id}\n"
            f"💵 Summa: {amount:,} so‘m\n"
            f"🏦 Bank: {bank_name}\n"
            f"💳 Karta: {card_number}\n"
            f"👤 Karta egasi: {card_holder}\n\n"
            "💳 To‘lov kartangizga yuboriladi.\n\n"
            "🔥 LEVEL_GROUP"
        ),
    )
    await callback.message.bot.send_message(
        chat_id=ADMIN_LOGS_CHANNEL_ID,
        text=(
            "✅ WITHDRAW TASDIQLANDI\n\n"
            f"🆔 Buyurtma: #{withdraw_id}\n"
            f"👤 Mijoz: {username}\n"
            f"🆔 Telegram ID: {telegram_id}\n\n"
            "🎮 Xizmat: UZS yechish\n"
            f"💵 Summa: {amount:,} so‘m\n"
            f"🏦 Bank: {bank_name}\n"
            f"💳 Karta: {card_number}\n"
            f"👤 Karta egasi: {card_holder}\n\n"
            f"👨‍💼 Admin: {admin_name}\n"
            f"⏳ Bajarish vaqti: {processing_time}\n"
            f"📩 Mijozga xabar: {'Yuborildi' if user_notified else 'Yuborilmadi'}"
        ),
    )

    await callback.message.bot.send_message(
        chat_id=COMPLETED_ORDERS_CHANNEL_ID,
        text=(
            "✅ PUL YECHISH BAJARILDI\n\n"
            f"🆔 Buyurtma: #{withdraw_id}\n"
            f"👤 Buyurtmachi: {username}\n"
            f"🆔 Telegram ID: {telegram_id}\n\n"
            "🎮 Xizmat: UZS yechish\n"
            f"💵 Summa: {amount:,} so‘m\n"
            f"🏦 Bank: {bank_name}\n"
            f"💳 Karta: {card_number}\n"
            f"👤 Karta egasi: {card_holder}\n\n"
            f"👨‍💼 Admin: {admin_name}\n"
            f"⏳ Bajarish vaqti: {processing_time}\n\n"
            "🔥 LEVEL_GROUP"
        ),
    )

    await callback.answer("✅ Withdraw tasdiqlandi.")


@router.callback_query(F.data.startswith("reject_withdraw_"))
async def reject_withdraw_handler(callback: CallbackQuery):
    withdraw_id = int(callback.data.replace("reject_withdraw_", ""))

    old_text = callback.message.text or ""
    if not withdraw_is_claimed(callback):
        await callback.answer("❌ Avval withdraw so‘rovini claim qiling.", show_alert=True)
        return
    action_key = await begin_action(callback, "reject_withdraw", withdraw_id)
    if not action_key:
        return
    username = get_line_value(old_text, "👤 Mijoz:")

    try:
        result = await reject_withdraw(
            withdraw_id=withdraw_id,
            admin_id=callback.from_user.id,
        )
    finally:
        active_actions.discard(action_key)

    if result.get("status_code") == 409:
        await callback.answer(
            "❌ Bu withdraw holati o‘zgargan yoki boshqa adminga biriktirilgan.",
            show_alert=True,
        )
        return

    if result.get("message") != "Withdraw rad etildi, pul balansga qaytarildi":
        await callback.answer(
            f"❌ Xatolik: {result.get('message', 'Nomaʼlum')}",
            show_alert=True,
        )
        return

    admin_name = get_admin_name(callback.from_user)
    processing_time = format_seconds(result.get("processing_seconds"))

    telegram_id = result.get("telegram_id")
    amount = int(result.get("amount", 0))
    bank_name = result.get("bank_name", "Nomaʼlum")
    card_number = result.get("card_number", "Nomaʼlum")
    card_holder = result.get("card_holder", "Nomaʼlum")
    reject_reason = result.get("reject_reason", "Admin rad etdi")

    await callback.message.edit_text(
        text=old_text.replace("📌 Status: CLAIMED", "🔴 Status: REJECTED"),
        reply_markup=None,
    )

    user_notified = await notify_user(
        bot=callback.message.bot,
        telegram_id=telegram_id,
        text=(
            "❌ Pul yechish so‘rovingiz rad etildi.\n\n"
            f"🆔 Buyurtma: #{withdraw_id}\n"
            f"💵 Summa: {amount:,} so‘m\n"
            f"🏦 Bank: {bank_name}\n"
            f"💳 Karta: {card_number}\n"
            f"👤 Karta egasi: {card_holder}\n\n"
            f"📌 Sabab: {reject_reason}\n\n"
            "💵 Mablag‘ balansingizga qaytarildi.\n\n"
            "🔥 LEVEL_GROUP"
        ),
    )

    await callback.message.bot.send_message(
        chat_id=ADMIN_LOGS_CHANNEL_ID,
        text=(
            "❌ WITHDRAW RAD ETILDI\n\n"
            f"🆔 Buyurtma: #{withdraw_id}\n"
            f"👤 Mijoz: {username}\n"
            f"🆔 Telegram ID: {telegram_id}\n\n"
            "🎮 Xizmat: UZS yechish\n"
            f"💵 Summa: {amount:,} so‘m\n"
            f"🏦 Bank: {bank_name}\n"
            f"💳 Karta: {card_number}\n"
            f"👤 Karta egasi: {card_holder}\n\n"
            f"👨‍💼 Admin: {admin_name}\n"
            f"📌 Sabab: {reject_reason}\n"
            f"⏳ Ko‘rib chiqish vaqti: {processing_time}\n"
            f"📩 Mijozga xabar: {'Yuborildi' if user_notified else 'Yuborilmadi'}"
        ),
    )

    await callback.answer("❌ Withdraw rad etildi.")
