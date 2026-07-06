from aiogram import Router, F
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from services.api import (
    create_p2p_order,
    get_open_p2p_orders,
    create_p2p_trade,
    approve_p2p_trade,
    reject_p2p_trade,
    confirm_p2p_trade,
    cancel_p2p_order,
    get_my_p2p_orders,
    update_p2p_order_price,
)

router = Router()

MIN_P2P_EFC = 50
MAX_P2P_EFC = 10000
MIN_PRICE_UZS = 1


class P2PState(StatesGroup):
    order_type = State()
    efc_amount = State()
    price_uzs = State()
    min_trade_efc = State()
    trade_amount = State()
    update_price = State()
    response_minutes = State()


def get_data(result):
    if isinstance(result, dict):
        return result.get("data") or result
    return {}


def is_success(result):
    return isinstance(result, dict) and result.get("success") is True


def p2p_menu_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📈 EFC sotish e’lonlari", callback_data="p2p_orders_SELL")],
            [InlineKeyboardButton(text="📉 EFC sotib olish e’lonlari", callback_data="p2p_orders_BUY")],
            [InlineKeyboardButton(text="➕ EFC sotish e’loni", callback_data="p2p_create_SELL")],
            [InlineKeyboardButton(text="➕ EFC sotib olish e’loni", callback_data="p2p_create_BUY")],
            [InlineKeyboardButton(text="📋 Mening e’lonlarim", callback_data="p2p_my_orders")],
        ]
    )


def p2p_response_time_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="⚡ 5 daqiqa", callback_data="p2p_time_5"),
                InlineKeyboardButton(text="🕙 10 daqiqa", callback_data="p2p_time_10"),
            ],
            [
                InlineKeyboardButton(text="🕒 15 daqiqa", callback_data="p2p_time_15"),
                InlineKeyboardButton(text="🕕 30 daqiqa", callback_data="p2p_time_30"),
            ],
            [InlineKeyboardButton(text="🕐 60 daqiqa", callback_data="p2p_time_60")],
        ]
    )


@router.message(F.text == "🤝 P2P Market")
async def p2p_menu(message: Message):
    await message.answer(
        "🤝 P2P Market\n\n"
        "Bu yerda EFC sotish va sotib olish e’lonlari mavjud.\n\n"
        "To‘lov karta orqali emas, ichki UZS/EFC balans orqali bo‘ladi.\n"
        "Savdo ikki tomon tasdiqlagandan keyin yakunlanadi.",
        reply_markup=p2p_menu_keyboard(),
    )


@router.callback_query(F.data == "p2p_menu")
async def p2p_menu_callback(callback: CallbackQuery):
    await callback.message.answer(
        "🤝 P2P Market\n\nKerakli bo‘limni tanlang:",
        reply_markup=p2p_menu_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("p2p_create_"))
async def p2p_create_start(callback: CallbackQuery, state: FSMContext):
    order_type = callback.data.replace("p2p_create_", "")

    if order_type not in ["BUY", "SELL"]:
        await callback.answer("Noto‘g‘ri e’lon turi.", show_alert=True)
        return

    await state.clear()
    await state.update_data(order_type=order_type)
    await state.set_state(P2PState.efc_amount)

    title = "EFC sotish" if order_type == "SELL" else "EFC sotib olish"

    await callback.message.answer(
        f"➕ {title} e’loni\n\n"
        "EFC miqdorini kiriting.\n\n"
        f"Minimal: {MIN_P2P_EFC} EFC\n"
        f"Maksimal: {MAX_P2P_EFC} EFC\n\n"
        "Masalan: 500"
    )
    await callback.answer()


@router.message(P2PState.efc_amount)
async def p2p_amount_handler(message: Message, state: FSMContext):
    try:
        efc_amount = float(message.text.replace(",", "."))
    except Exception:
        await message.answer("❌ Faqat raqam kiriting. Masalan: 500")
        return

    if efc_amount < MIN_P2P_EFC:
        await message.answer(f"❌ Minimal e’lon {MIN_P2P_EFC} EFC.")
        return

    if efc_amount > MAX_P2P_EFC:
        await message.answer(f"❌ Maksimal e’lon {MAX_P2P_EFC} EFC.")
        return

    await state.update_data(efc_amount=efc_amount)
    await state.set_state(P2PState.price_uzs)

    await message.answer(
        "💵 1 EFC narxini UZS’da kiriting.\n\n"
        "Masalan: 100"
    )
@router.message(P2PState.price_uzs)
async def p2p_price_handler(message: Message, state: FSMContext):
    try:
        price_uzs = float(message.text.replace(",", "."))
    except Exception:
        await message.answer("❌ Faqat raqam kiriting. Masalan: 100")
        return

    if price_uzs < MIN_PRICE_UZS:
        await message.answer("❌ Narx 1 UZS dan kam bo‘lmaydi.")
        return

    await state.update_data(price_uzs=price_uzs)
    await state.set_state(P2PState.min_trade_efc)

    await message.answer(
        "📌 Minimal savdo miqdorini kiriting.\n\n"
        f"Eng kami: {MIN_P2P_EFC} EFC\n"
        "Masalan: 50 yoki 100"
    )


@router.message(P2PState.min_trade_efc)
async def p2p_min_trade_handler(message: Message, state: FSMContext):
    try:
        min_trade_efc = float(message.text.replace(",", "."))
    except Exception:
        await message.answer("❌ Faqat raqam kiriting. Masalan: 50")
        return

    data = await state.get_data()
    efc_amount = data["efc_amount"]

    if min_trade_efc < MIN_P2P_EFC:
        await message.answer(f"❌ Minimal savdo {MIN_P2P_EFC} EFC dan kam bo‘lmaydi.")
        return

    if min_trade_efc > efc_amount:
        await message.answer("❌ Minimal savdo e’lon miqdoridan katta bo‘lmaydi.")
        return

    await state.update_data(min_trade_efc=min_trade_efc)
    await state.set_state(P2PState.response_minutes)

    await message.answer(
        "⏱ Xaridor javob berish vaqtini tanlang.\n\n"
        "Xaridor buyurtma olgandan keyin shu vaqt ichida javob berishi kerak:",
        reply_markup=p2p_response_time_keyboard(),
    )


@router.callback_query(F.data.startswith("p2p_time_"))
async def p2p_response_time_selected(callback: CallbackQuery, state: FSMContext):
    response_minutes = int(callback.data.replace("p2p_time_", ""))

    data = await state.get_data()

    order_type = data["order_type"]
    efc_amount = data["efc_amount"]
    price_uzs = data["price_uzs"]
    min_trade_efc = data["min_trade_efc"]

    result = await create_p2p_order(
        telegram_id=callback.from_user.id,
        order_type=order_type,
        efc_amount=efc_amount,
        price_uzs=price_uzs,
        min_trade_efc=min_trade_efc,
        response_minutes=response_minutes,
    )

    await state.clear()

    if not is_success(result):
        await callback.message.answer(
            "❌ P2P e’lon yaratilmadi.\n\n"
            f"Sabab: {result.get('message', 'Backend error')}",
            reply_markup=p2p_menu_keyboard(),
        )
        await callback.answer()
        return

    order = get_data(result)
    title = "SOTISH" if order_type == "SELL" else "SOTIB OLISH"
    total_uzs = efc_amount * price_uzs

    await callback.message.answer(
        f"✅ P2P {title} e’loni yaratildi!\n\n"
        f"🆔 Order: #{order.get('id')}\n"
        f"🪙 EFC: {efc_amount}\n"
        f"💵 1 EFC narxi: {price_uzs:,.2f} UZS\n"
        f"💰 Umumiy qiymat: {total_uzs:,.2f} UZS\n"
        f"📌 Minimal savdo: {min_trade_efc} EFC\n"
        f"⏱ Javob vaqti: {response_minutes} daqiqa\n\n"
        "E’lon P2P Marketda ko‘rinadi.",
        reply_markup=p2p_menu_keyboard(),
    )

    await callback.answer("✅ E’lon yaratildi.")


@router.callback_query(F.data.startswith("p2p_orders_"))
async def p2p_open_orders(callback: CallbackQuery):
    order_type = callback.data.replace("p2p_orders_", "")
    result = await get_open_p2p_orders(order_type=order_type)

    orders = result.get("data", []) if isinstance(result, dict) else result

    if not orders:
        await callback.message.answer(
            "📋 Hozircha ochiq e’lonlar yo‘q.",
            reply_markup=p2p_menu_keyboard(),
        )
        await callback.answer()
        return

    title = "EFC sotish e’lonlari" if order_type == "SELL" else "EFC sotib olish e’lonlari"
    await callback.message.answer(f"📋 {title}")

    for order in orders[:10]:
        order_id = order.get("id")
        remaining = float(order.get("remaining_efc", 0))
        price = float(order.get("price_uzs", 0))
        min_trade = float(order.get("min_trade_efc", 0))
        response_minutes = int(order.get("response_minutes", 15))

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🤝 Savdo qilish",
                        callback_data=f"p2p_trade_{order_id}",
                    )
                ]
            ]
        )

        await callback.message.answer(
            f"🆔 Order: #{order_id}\n"
            f"📌 Tur: {order_type}\n"
            f"🪙 Qolgan EFC: {remaining}\n"
            f"💵 1 EFC: {price:,.2f} UZS\n"
            f"🔻 Minimal savdo: {min_trade} EFC\n"
            f"⏱ Javob vaqti: {response_minutes} daqiqa",
            reply_markup=keyboard,
        )

    await callback.answer()


@router.callback_query(F.data.startswith("p2p_trade_"))
async def p2p_trade_start(callback: CallbackQuery, state: FSMContext):
    order_id = int(callback.data.replace("p2p_trade_", ""))

    await state.clear()
    await state.update_data(order_id=order_id)
    await state.set_state(P2PState.trade_amount)

    await callback.message.answer(
        "🤝 Savdo miqdorini kiriting.\n\n"
        "Masalan: 50"
    )
    await callback.answer()
@router.message(P2PState.trade_amount)
async def p2p_trade_amount_handler(message: Message, state: FSMContext):
    try:
        efc_amount = float(message.text.replace(",", "."))
    except Exception:
        await message.answer("❌ Faqat raqam kiriting. Masalan: 50")
        return

    if efc_amount < MIN_P2P_EFC:
        await message.answer(f"❌ Minimal savdo {MIN_P2P_EFC} EFC.")
        return

    data = await state.get_data()
    order_id = data["order_id"]

    result = await create_p2p_trade(
        order_id=order_id,
        telegram_id=message.from_user.id,
        efc_amount=efc_amount,
    )

    await state.clear()

    if not is_success(result):
        await message.answer(
            "❌ Savdo so‘rovi yuborilmadi.\n\n"
            f"Sabab: {result.get('message', 'Noma’lum xatolik')}",
            reply_markup=p2p_menu_keyboard(),
        )
        return

    trade = get_data(result)
    trade_id = trade.get("id")
    owner_id = trade.get("owner_id")
    response_minutes = trade.get("response_minutes", 15)

    owner_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Tasdiqlash",
                    callback_data=f"p2p_owner_approve_{trade_id}",
                ),
                InlineKeyboardButton(
                    text="❌ Rad etish",
                    callback_data=f"p2p_owner_reject_{trade_id}",
                ),
            ]
        ]
    )

    await message.bot.send_message(
        chat_id=owner_id,
        text=(
            "🤝 Sizning P2P e’loningizga savdo so‘rovi keldi.\n\n"
            f"🆔 Trade: #{trade_id}\n"
            f"🪙 EFC: {trade.get('efc_amount')}\n"
            f"💵 1 EFC: {trade.get('price_uzs')} UZS\n"
            f"💰 Jami: {trade.get('total_uzs')} UZS\n"
            f"⏱ Javob vaqti: {response_minutes} daqiqa\n\n"
            "Tasdiqlaysizmi?"
        ),
        reply_markup=owner_keyboard,
    )

    await message.answer(
        "✅ Savdo so‘rovi yuborildi.\n\n"
        "E’lon egasi tasdiqlashini kuting.",
        reply_markup=p2p_menu_keyboard(),
    )


@router.callback_query(F.data.startswith("p2p_owner_approve_"))
async def p2p_owner_approve(callback: CallbackQuery):
    trade_id = int(callback.data.replace("p2p_owner_approve_", ""))

    result = await approve_p2p_trade(
        trade_id=trade_id,
        telegram_id=callback.from_user.id,
    )

    if not is_success(result):
        await callback.answer(result.get("message", "Xatolik"), show_alert=True)
        return

    trade = get_data(result)
    requester_id = trade.get("requester_id")

    requester_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Yakuniy tasdiqlash",
                    callback_data=f"p2p_requester_confirm_{trade_id}",
                )
            ]
        ]
    )

    await callback.bot.send_message(
        chat_id=requester_id,
        text=(
            "✅ E’lon egasi savdoni tasdiqladi.\n\n"
            f"🆔 Trade: #{trade_id}\n"
            f"🪙 EFC: {trade.get('efc_amount')}\n"
            f"💰 Jami: {trade.get('total_uzs')} UZS\n\n"
            "Savdoni yakunlash uchun tasdiqlang."
        ),
        reply_markup=requester_keyboard,
    )

    await callback.message.edit_text(
        "✅ Savdo tasdiqlandi. Ikkinchi tomon yakuniy tasdiqlashi kutilmoqda."
    )
    await callback.answer("Tasdiqlandi.")


@router.callback_query(F.data.startswith("p2p_owner_reject_"))
async def p2p_owner_reject(callback: CallbackQuery):
    trade_id = int(callback.data.replace("p2p_owner_reject_", ""))

    result = await reject_p2p_trade(
        trade_id=trade_id,
        telegram_id=callback.from_user.id,
    )

    if not is_success(result):
        await callback.answer(result.get("message", "Xatolik"), show_alert=True)
        return

    trade = get_data(result)
    requester_id = trade.get("requester_id")

    await callback.bot.send_message(
        chat_id=requester_id,
        text=f"❌ P2P savdo #{trade_id} e’lon egasi tomonidan rad etildi.",
    )

    await callback.message.edit_text("❌ Savdo rad etildi.")
    await callback.answer("Rad etildi.")


@router.callback_query(F.data.startswith("p2p_requester_confirm_"))
async def p2p_requester_confirm(callback: CallbackQuery):
    trade_id = int(callback.data.replace("p2p_requester_confirm_", ""))

    result = await confirm_p2p_trade(
        trade_id=trade_id,
        telegram_id=callback.from_user.id,
    )

    if not is_success(result):
        await callback.answer(result.get("message", "Xatolik"), show_alert=True)
        return

    trade = get_data(result)

    await callback.bot.send_message(
        chat_id=trade.get("owner_id"),
        text=(
            "✅ P2P savdo yakunlandi!\n\n"
            f"🆔 Trade: #{trade_id}\n"
            f"🪙 EFC: {trade.get('efc_amount')}\n"
            f"💰 UZS: {trade.get('total_uzs')}"
        ),
    )

    await callback.message.edit_text(
        "✅ P2P savdo yakunlandi!\n\n"
        f"🆔 Trade: #{trade_id}\n"
        f"🪙 EFC: {trade.get('efc_amount')}\n"
        f"💰 UZS: {trade.get('total_uzs')}\n\n"
        "Balanslar avtomatik yangilandi."
    )

    await callback.answer("Savdo yakunlandi.")


@router.callback_query(F.data.startswith("p2p_cancel_order_"))
async def p2p_cancel_order(callback: CallbackQuery):
    order_id = int(callback.data.replace("p2p_cancel_order_", ""))

    result = await cancel_p2p_order(
        order_id=order_id,
        telegram_id=callback.from_user.id,
    )

    if not is_success(result):
        await callback.answer(result.get("message", "Xatolik"), show_alert=True)
        return

    await callback.message.edit_text("❌ P2P e’lon bekor qilindi.")
    await callback.answer("Bekor qilindi.")


@router.callback_query(F.data == "p2p_my_orders")
async def p2p_my_orders(callback: CallbackQuery):
    result = await get_my_p2p_orders(callback.from_user.id)
    orders = result.get("data", []) if isinstance(result, dict) else result

    if not orders:
        await callback.message.answer("📋 Sizda P2P e’lonlar yo‘q.")
        await callback.answer()
        return

    for order in orders[:10]:
        order_id = order.get("id")
        status = order.get("status")
        price = float(order.get("price_uzs", 0))
        remaining = float(order.get("remaining_efc", 0))

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="💵 Narxni o‘zgartirish",
                        callback_data=f"p2p_update_price_{order_id}",
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="❌ E’lonni bekor qilish",
                        callback_data=f"p2p_cancel_order_{order_id}",
                    )
                ],
            ]
        )

        await callback.message.answer(
            f"📋 Mening e’lonim #{order_id}\n\n"
            f"📌 Status: {status}\n"
            f"🪙 Qolgan EFC: {remaining}\n"
            f"💵 1 EFC narxi: {price:,.2f} UZS",
            reply_markup=keyboard,
        )

    await callback.answer()


@router.callback_query(F.data.startswith("p2p_update_price_"))
async def p2p_update_price_start(callback: CallbackQuery, state: FSMContext):
    order_id = int(callback.data.replace("p2p_update_price_", ""))

    await state.clear()
    await state.update_data(update_order_id=order_id)
    await state.set_state(P2PState.update_price)

    await callback.message.answer("💵 Yangi 1 EFC narxini kiriting. Masalan: 120")
    await callback.answer()


@router.message(P2PState.update_price)
async def p2p_update_price_finish(message: Message, state: FSMContext):
    try:
        price_uzs = float(message.text.replace(",", "."))
    except Exception:
        await message.answer("❌ Faqat raqam kiriting. Masalan: 120")
        return

    data = await state.get_data()
    order_id = data["update_order_id"]

    result = await update_p2p_order_price(
        order_id=order_id,
        telegram_id=message.from_user.id,
        price_uzs=price_uzs,
    )

    await state.clear()

    if not is_success(result):
        await message.answer(f"❌ {result.get('message', 'Xatolik')}")
        return

    await message.answer("✅ P2P e’lon narxi yangilandi.")
