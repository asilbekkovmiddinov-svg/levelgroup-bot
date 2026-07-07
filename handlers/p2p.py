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
    get_my_p2p_trades,
    get_p2p_history,
    update_p2p_order_price,
    update_p2p_order_amount,
    update_p2p_order_min_trade,
    update_p2p_order_response_minutes,
)

router = Router()

MIN_P2P_EFC = 50
MAX_P2P_EFC = 10000
MIN_PRICE_UZS = 1


class P2PState(StatesGroup):
    efc_amount = State()
    price_uzs = State()
    min_trade_efc = State()
    response_minutes = State()
    trade_amount = State()
    update_price = State()
    update_amount = State()
    update_min_trade = State()


def get_data(result):
    if isinstance(result, dict):
        return result.get("data") or result
    return {}


def is_success(result):
    return isinstance(result, dict) and result.get("success") is True


def format_money(value):
    try:
        return f"{float(value):,.2f}"
    except Exception:
        return str(value)


def format_efc(value):
    try:
        return f"{float(value):,.4f}".rstrip("0").rstrip(".")
    except Exception:
        return str(value)


def get_remaining_text(item):
    if not isinstance(item, dict):
        return "00:00"

    return item.get("remaining_text") or "00:00"


def p2p_menu_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📈 EFC sotish e’lonlari",
                    callback_data="p2p_orders_SELL",
                )
            ],
            [
                InlineKeyboardButton(
                    text="📉 EFC sotib olish e’lonlari",
                    callback_data="p2p_orders_BUY",
                )
            ],
            [
                InlineKeyboardButton(
                    text="➕ EFC sotish e’loni",
                    callback_data="p2p_create_SELL",
                )
            ],
            [
                InlineKeyboardButton(
                    text="➕ EFC sotib olish e’loni",
                    callback_data="p2p_create_BUY",
                )
            ],
            [
                InlineKeyboardButton(
                    text="📋 Mening e’lonlarim",
                    callback_data="p2p_my_orders",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🧾 Mening buyurtmalarim",
                    callback_data="p2p_my_trades",
                )
            ],
            [
                InlineKeyboardButton(
                    text="📜 P2P tarix",
                    callback_data="p2p_history_menu",
                )
            ],
        ]
    )


def p2p_response_time_keyboard(prefix="p2p_time"):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⚡ 5 daqiqa",
                    callback_data=f"{prefix}_5",
                ),
                InlineKeyboardButton(
                    text="🕙 10 daqiqa",
                    callback_data=f"{prefix}_10",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🕒 15 daqiqa",
                    callback_data=f"{prefix}_15",
                ),
                InlineKeyboardButton(
                    text="🕕 30 daqiqa",
                    callback_data=f"{prefix}_30",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🕐 60 daqiqa",
                    callback_data=f"{prefix}_60",
                )
            ],
        ]
    )


def history_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Yakunlanganlar",
                    callback_data="p2p_history_COMPLETED",
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Rad etilganlar",
                    callback_data="p2p_history_REJECTED",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⏳ Timeout bo‘lganlar",
                    callback_data="p2p_history_TIMEOUT",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🚫 Bekor qilinganlar",
                    callback_data="p2p_history_CANCELLED",
                )
            ],
            [
                InlineKeyboardButton(
                    text="📜 Hammasi",
                    callback_data="p2p_history_ALL",
                )
            ],
        ]
    )


@router.message(F.text == "🤝 P2P Market")
async def p2p_menu(message: Message):
    await message.answer(
        "🤝 P2P Market\n\n"
        "Bu yerda EFC sotish va sotib olish e’lonlari mavjud.\n\n"
        "Savdo ikki tomon tasdiqlagandan keyin yakunlanadi.\n"
        "Komissiya: 2.5% EFC + 2.5% UZS.",
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
        await message.answer(
            f"❌ Minimal savdo {MIN_P2P_EFC} EFC dan kam bo‘lmaydi."
        )
        return

    if min_trade_efc > efc_amount:
        await message.answer("❌ Minimal savdo e’lon miqdoridan katta bo‘lmaydi.")
        return

    await state.update_data(min_trade_efc=min_trade_efc)
    await state.set_state(P2PState.response_minutes)

    await message.answer(
        "⏱ Javob vaqtini tanlang.\n\n"
        "Savdo ochilganda shu vaqt ichida tasdiqlash kerak bo‘ladi:",
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
        f"🪙 EFC: {format_efc(efc_amount)}\n"
        f"💵 1 EFC narxi: {format_money(price_uzs)} UZS\n"
        f"💰 Umumiy qiymat: {format_money(total_uzs)} UZS\n"
        f"📌 Minimal savdo: {format_efc(min_trade_efc)} EFC\n"
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

    title = (
        "EFC sotish e’lonlari"
        if order_type == "SELL"
        else "EFC sotib olish e’lonlari"
    )

    await callback.message.answer(f"📋 {title}")

    for order in orders[:10]:
        order_id = order.get("id")
        remaining = order.get("remaining_efc", 0)
        price = order.get("price_uzs", 0)
        min_trade = order.get("min_trade_efc", 0)
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
            f"{order.get('owner_online_text', '⚪ Offline')}\n"
            f"🕒 Oxirgi faollik: {order.get('owner_last_seen_text', 'Noma’lum')}\n"
            f"🪙 Qolgan EFC: {format_efc(remaining)}\n"
            f"💵 1 EFC: {format_money(price)} UZS\n"
            f"🔻 Minimal savdo: {format_efc(min_trade)} EFC\n"
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
    remaining = get_remaining_text(trade)

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
            f"🪙 EFC: {format_efc(trade.get('efc_amount'))}\n"
            f"💵 1 EFC: {format_money(trade.get('price_uzs'))} UZS\n"
            f"💰 Jami: {format_money(trade.get('total_uzs'))} UZS\n"
            f"⏱ Javob vaqti: {response_minutes} daqiqa\n"
            f"⏳ Qolgan vaqt: {remaining}\n\n"
            "Tasdiqlaysizmi?"
        ),
        reply_markup=owner_keyboard,
    )

    await message.answer(
        "✅ Savdo so‘rovi yuborildi.\n\n"
        f"⏳ Qolgan vaqt: {remaining}\n"
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
    remaining = get_remaining_text(trade)

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
            f"🪙 EFC: {format_efc(trade.get('efc_amount'))}\n"
            f"💵 1 EFC: {format_money(trade.get('price_uzs'))} UZS\n"
            f"💰 Jami: {format_money(trade.get('total_uzs'))} UZS\n"
            f"⏳ Qolgan vaqt: {remaining}\n\n"
            "Savdoni yakunlash uchun tasdiqlang."
        ),
        reply_markup=requester_keyboard,
    )

    await callback.message.edit_text(
        "✅ Savdo tasdiqlandi.\n\n"
        "Ikkinchi tomon yakuniy tasdiqlashi kutilmoqda.\n"
        f"⏳ Qolgan vaqt: {remaining}"
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
            f"🪙 EFC: {format_efc(trade.get('efc_amount'))}\n"
            f"💰 UZS: {format_money(trade.get('total_uzs'))}"
        ),
    )

    await callback.message.edit_text(
        "✅ P2P savdo yakunlandi!\n\n"
        f"🆔 Trade: #{trade_id}\n"
        f"🪙 EFC: {format_efc(trade.get('efc_amount'))}\n"
        f"💰 UZS: {format_money(trade.get('total_uzs'))}\n\n"
        "Balanslar avtomatik yangilandi."
    )

    await callback.answer("Savdo yakunlandi.")


@router.callback_query(F.data == "p2p_my_orders")
async def p2p_my_orders(callback: CallbackQuery):
    result = await get_my_p2p_orders(callback.from_user.id)
    orders = result.get("data", []) if isinstance(result, dict) else result

    if not orders:
        await callback.message.answer(
            "📋 Sizda P2P e’lonlar yo‘q.",
            reply_markup=p2p_menu_keyboard(),
        )
        await callback.answer()
        return

    await callback.message.answer("📋 Mening P2P e’lonlarim")

    for order in orders[:10]:
        order_id = order.get("id")
        status = order.get("status")
        order_type = order.get("order_type")
        price = order.get("price_uzs", 0)
        remaining = order.get("remaining_efc", 0)
        min_trade = order.get("min_trade_efc", 0)
        response_minutes = order.get("response_minutes", 15)

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="💵 Narx",
                        callback_data=f"p2p_update_price_{order_id}",
                    ),
                    InlineKeyboardButton(
                        text="🪙 Miqdor",
                        callback_data=f"p2p_update_amount_{order_id}",
                    ),
                ],
                [
                    InlineKeyboardButton(
                        text="📌 Minimum",
                        callback_data=f"p2p_update_min_{order_id}",
                    ),
                    InlineKeyboardButton(
                        text="⏱ Vaqt",
                        callback_data=f"p2p_update_time_{order_id}",
                    ),
                ],
                [
                    InlineKeyboardButton(
                        text="❌ Bekor qilish",
                        callback_data=f"p2p_cancel_order_{order_id}",
                    )
                ],
            ]
        )

        await callback.message.answer(
            f"📋 E’lon #{order_id}\n\n"
            f"📌 Tur: {order_type}\n"
            f"📌 Status: {status}\n"
            f"🪙 Qolgan EFC: {format_efc(remaining)}\n"
            f"💵 1 EFC narxi: {format_money(price)} UZS\n"
            f"🔻 Minimal savdo: {format_efc(min_trade)} EFC\n"
            f"⏱ Javob vaqti: {response_minutes} daqiqa",
            reply_markup=keyboard,
        )

    await callback.answer()


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


@router.callback_query(F.data.startswith("p2p_update_price_"))
async def p2p_update_price_start(callback: CallbackQuery, state: FSMContext):
    order_id = int(callback.data.replace("p2p_update_price_", ""))

    await state.clear()
    await state.update_data(update_order_id=order_id)
    await state.set_state(P2PState.update_price)

    await callback.message.answer(
        "💵 Yangi 1 EFC narxini kiriting.\n\n"
        "Masalan: 120"
    )
    await callback.answer()


@router.message(P2PState.update_price)
async def p2p_update_price_finish(message: Message, state: FSMContext):
    try:
        price_uzs = float(message.text.replace(",", "."))
    except Exception:
        await message.answer("❌ Faqat raqam kiriting. Masalan: 120")
        return

    if price_uzs < MIN_PRICE_UZS:
        await message.answer("❌ Narx 1 UZS dan kam bo‘lmaydi.")
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

    await message.answer(
        "✅ P2P e’lon narxi yangilandi.",
        reply_markup=p2p_menu_keyboard(),
    )
@router.callback_query(F.data.startswith("p2p_update_amount_"))
async def p2p_update_amount_start(callback: CallbackQuery, state: FSMContext):
    order_id = int(callback.data.replace("p2p_update_amount_", ""))

    await state.clear()
    await state.update_data(update_order_id=order_id)
    await state.set_state(P2PState.update_amount)

    await callback.message.answer(
        "🪙 Yangi umumiy EFC miqdorini kiriting.\n\n"
        "Masalan: 500"
    )
    await callback.answer()


@router.message(P2PState.update_amount)
async def p2p_update_amount_finish(message: Message, state: FSMContext):
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

    data = await state.get_data()
    order_id = data["update_order_id"]

    result = await update_p2p_order_amount(
        order_id=order_id,
        telegram_id=message.from_user.id,
        efc_amount=efc_amount,
    )

    await state.clear()

    if not is_success(result):
        await message.answer(f"❌ {result.get('message', 'Xatolik')}")
        return

    await message.answer(
        "✅ P2P e’lon miqdori yangilandi.",
        reply_markup=p2p_menu_keyboard(),
    )


@router.callback_query(F.data.startswith("p2p_update_min_"))
async def p2p_update_min_start(callback: CallbackQuery, state: FSMContext):
    order_id = int(callback.data.replace("p2p_update_min_", ""))

    await state.clear()
    await state.update_data(update_order_id=order_id)
    await state.set_state(P2PState.update_min_trade)

    await callback.message.answer(
        "📌 Yangi minimal savdo miqdorini kiriting.\n\n"
        "Masalan: 50"
    )
    await callback.answer()


@router.message(P2PState.update_min_trade)
async def p2p_update_min_finish(message: Message, state: FSMContext):
    try:
        min_trade_efc = float(message.text.replace(",", "."))
    except Exception:
        await message.answer("❌ Faqat raqam kiriting. Masalan: 50")
        return

    if min_trade_efc < MIN_P2P_EFC:
        await message.answer(f"❌ Minimal savdo {MIN_P2P_EFC} EFC dan kam bo‘lmaydi.")
        return

    data = await state.get_data()
    order_id = data["update_order_id"]

    result = await update_p2p_order_min_trade(
        order_id=order_id,
        telegram_id=message.from_user.id,
        min_trade_efc=min_trade_efc,
    )

    await state.clear()

    if not is_success(result):
        await message.answer(f"❌ {result.get('message', 'Xatolik')}")
        return

    await message.answer(
        "✅ Minimal savdo miqdori yangilandi.",
        reply_markup=p2p_menu_keyboard(),
    )


@router.callback_query(F.data.startswith("p2p_update_time_"))
async def p2p_update_time_start(callback: CallbackQuery, state: FSMContext):
    order_id = int(callback.data.replace("p2p_update_time_", ""))

    await state.clear()
    await state.update_data(update_order_id=order_id)

    await callback.message.answer(
        "⏱ Yangi javob vaqtini tanlang:",
        reply_markup=p2p_response_time_keyboard(prefix="p2p_edit_time"),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("p2p_edit_time_"))
async def p2p_update_time_finish(callback: CallbackQuery, state: FSMContext):
    response_minutes = int(callback.data.replace("p2p_edit_time_", ""))

    data = await state.get_data()
    order_id = data.get("update_order_id")

    if not order_id:
        await callback.answer("E’lon topilmadi.", show_alert=True)
        return

    result = await update_p2p_order_response_minutes(
        order_id=order_id,
        telegram_id=callback.from_user.id,
        response_minutes=response_minutes,
    )

    await state.clear()

    if not is_success(result):
        await callback.message.answer(f"❌ {result.get('message', 'Xatolik')}")
        await callback.answer()
        return

    await callback.message.answer(
        "✅ Javob vaqti yangilandi.",
        reply_markup=p2p_menu_keyboard(),
    )
    await callback.answer("Yangilandi.")


@router.callback_query(F.data == "p2p_my_trades")
async def p2p_my_trades(callback: CallbackQuery):
    result = await get_my_p2p_trades(callback.from_user.id)
    trades = result.get("data", []) if isinstance(result, dict) else result

    if not trades:
        await callback.message.answer(
            "🧾 Sizda P2P buyurtmalar yo‘q.",
            reply_markup=p2p_menu_keyboard(),
        )
        await callback.answer()
        return

    await callback.message.answer("🧾 Mening P2P buyurtmalarim")

    for trade in trades[:10]:
        trade_id = trade.get("id")
        status = trade.get("status")
        remaining = get_remaining_text(trade)

        buttons = []

        if (
            trade.get("requester_id") == callback.from_user.id
            and status == "OWNER_APPROVED"
        ):
            buttons.append(
                [
                    InlineKeyboardButton(
                        text="✅ Yakuniy tasdiqlash",
                        callback_data=f"p2p_requester_confirm_{trade_id}",
                    )
                ]
            )

        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons) if buttons else None

        await callback.message.answer(
            f"🧾 Trade #{trade_id}\n\n"
            f"📌 Status: {status}\n"
            f"📌 Tur: {trade.get('order_type')}\n"
            f"🪙 EFC: {format_efc(trade.get('efc_amount'))}\n"
            f"💵 1 EFC: {format_money(trade.get('price_uzs'))} UZS\n"
            f"💰 Jami: {format_money(trade.get('total_uzs'))} UZS\n"
            f"🔥 EFC komissiya: {format_efc(trade.get('efc_fee'))}\n"
            f"💸 UZS komissiya: {format_money(trade.get('uzs_fee'))} UZS\n"
            f"⏳ Qolgan vaqt: {remaining}",
            reply_markup=keyboard,
        )

    await callback.answer()


@router.callback_query(F.data == "p2p_history_menu")
async def p2p_history_menu(callback: CallbackQuery):
    await callback.message.answer(
        "📜 P2P tarix\n\nQaysi tarixni ko‘rmoqchisiz?",
        reply_markup=history_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("p2p_history_"))
async def p2p_history(callback: CallbackQuery):
    status = callback.data.replace("p2p_history_", "")

    api_status = None if status == "ALL" else status

    result = await get_p2p_history(
        telegram_id=callback.from_user.id,
        status=api_status,
    )

    trades = result.get("data", []) if isinstance(result, dict) else result

    if not trades:
        await callback.message.answer(
            "📜 Bu bo‘yicha tarix topilmadi.",
            reply_markup=p2p_menu_keyboard(),
        )
        await callback.answer()
        return

    await callback.message.answer("📜 P2P tarix")

    for trade in trades[:15]:
        role = (
            "Sotuvchi / e’lon egasi"
            if trade.get("owner_id") == callback.from_user.id
            else "Requester / savdo boshlagan"
        )

        await callback.message.answer(
            f"📜 Trade #{trade.get('id')}\n\n"
            f"👤 Rol: {role}\n"
            f"📌 Status: {trade.get('status')}\n"
            f"📌 Tur: {trade.get('order_type')}\n"
            f"🪙 EFC: {format_efc(trade.get('efc_amount'))}\n"
            f"💵 1 EFC: {format_money(trade.get('price_uzs'))} UZS\n"
            f"💰 Jami: {format_money(trade.get('total_uzs'))} UZS\n"
            f"🔥 EFC komissiya: {format_efc(trade.get('efc_fee'))}\n"
            f"💸 UZS komissiya: {format_money(trade.get('uzs_fee'))} UZS\n"
            f"📅 Sana: {trade.get('created_at')}"
        )

    await callback.answer()
