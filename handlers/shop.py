from decimal import Decimal, InvalidOperation

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from services.api import buy_shop_efc, buy_shop_tickets, get_shop_catalog


router = Router()


class ShopState(StatesGroup):
    efc_amount = State()
    ticket_quantity = State()


def parse_efc_amount(value: str) -> Decimal | None:
    normalized = str(value or "").replace(" ", "").replace(",", ".").strip()
    try:
        amount = Decimal(normalized)
    except (InvalidOperation, ValueError):
        return None
    if amount <= 0 or amount.as_tuple().exponent < -2:
        return None
    return amount


def parse_ticket_quantity(value: str) -> int | None:
    normalized = str(value or "").replace(" ", "").strip()
    if not normalized.isdigit():
        return None
    quantity = int(normalized)
    return quantity if quantity > 0 else None


def money(value) -> str:
    try:
        number = Decimal(str(value))
        return f"{number:,.2f}".replace(",", " ")
    except (InvalidOperation, ValueError):
        return "0.00"


def shop_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🪙 EFC sotib olish", callback_data="shop:efc")],
        [InlineKeyboardButton(text="🎟 Arena Ticket olish", callback_data="shop:ticket")],
        [InlineKeyboardButton(text="🔄 Yangilash", callback_data="shop:open")],
    ])


def cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="❌ Bekor qilish", callback_data="shop:open")
    ]])


def _catalog_data(payload: dict) -> dict | None:
    if not isinstance(payload, dict) or not payload.get("success"):
        return None
    data = payload.get("data")
    return data if isinstance(data, dict) else None


async def send_shop_menu(message: Message):
    try:
        payload = await get_shop_catalog(message.chat.id)
    except Exception:
        payload = None
    data = _catalog_data(payload or {})
    if data is None:
        detail = (payload or {}).get("message") if isinstance(payload, dict) else None
        await message.answer(
            f"❌ Magazin ochilmadi. {detail or 'Qayta urinib ko‘ring.'}"
        )
        return

    await message.answer(
        "🛍 <b>LEVEL_GROUP MAGAZIN</b>\n\n"
        f"💵 UZS balans: <b>{money(data['uzs_balance'])} so‘m</b>\n"
        f"🪙 EFC balans: <b>{money(data['efc_balance'])} EFC</b>\n"
        f"🎟 Arena Ticket: <b>{int(data['ticket_balance'])}</b>\n\n"
        f"📌 1 EFC = <b>{money(data['efc_price_uzs'])} so‘m</b>\n"
        f"📌 1 Ticket = <b>{money(data['ticket_price_efc'])} EFC</b>",
        reply_markup=shop_keyboard(),
    )


@router.message(Command("shop"))
@router.message(F.text == "🛍 Magazin")
async def shop_command(message: Message, state: FSMContext):
    await state.clear()
    await send_shop_menu(message)


@router.callback_query(F.data == "shop:open")
async def shop_open(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer()
    await send_shop_menu(callback.message)


@router.callback_query(F.data == "shop:efc")
async def shop_efc_start(callback: CallbackQuery, state: FSMContext):
    try:
        payload = await get_shop_catalog(callback.from_user.id)
    except Exception:
        payload = None
    data = _catalog_data(payload or {})
    if data is None:
        await callback.answer(
            (payload or {}).get("message", "Magazin vaqtincha ishlamayapti"),
            show_alert=True,
        )
        return
    await state.set_state(ShopState.efc_amount)
    await state.update_data(
        efc_price_uzs=str(data["efc_price_uzs"]),
        max_efc=str(data["max_efc_per_purchase"]),
    )
    await callback.message.answer(
        "🪙 <b>EFC sotib olish</b>\n\n"
        f"1 EFC = {money(data['efc_price_uzs'])} so‘m\n"
        f"UZS balans: {money(data['uzs_balance'])} so‘m\n\n"
        "Sotib olmoqchi bo‘lgan EFC miqdorini yozing.\n"
        "Masalan: <code>10</code>",
        reply_markup=cancel_keyboard(),
    )
    await callback.answer()


@router.message(ShopState.efc_amount)
async def shop_efc_quote(message: Message, state: FSMContext):
    amount = parse_efc_amount(message.text)
    state_data = await state.get_data()
    maximum = Decimal(state_data.get("max_efc", "0"))
    if amount is None or amount > maximum:
        await message.answer(
            f"❌ 0 dan katta va {money(maximum)} dan oshmagan miqdor kiriting."
        )
        return
    price = Decimal(state_data["efc_price_uzs"])
    cost = amount * price
    await state.clear()
    await message.answer(
        "🧾 <b>Xaridni tasdiqlang</b>\n\n"
        f"🪙 EFC: <b>{money(amount)}</b>\n"
        f"💵 Narx: <b>{money(cost)} so‘m</b>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="✅ Sotib olish",
                callback_data=f"shop:confirm:efc:{amount}",
            )],
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="shop:open")],
        ]),
    )


@router.callback_query(F.data.startswith("shop:confirm:efc:"))
async def shop_efc_confirm(callback: CallbackQuery):
    amount = parse_efc_amount((callback.data or "").rsplit(":", 1)[-1])
    if amount is None:
        await callback.answer("Miqdor noto‘g‘ri", show_alert=True)
        return
    key = f"bot-shop-efc:{callback.from_user.id}:{callback.message.message_id}"
    try:
        payload = await buy_shop_efc(callback.from_user.id, amount, key)
    except Exception:
        payload = None
    data = _catalog_data(payload or {})
    if data is None:
        await callback.answer(
            (payload or {}).get("message", "Xarid bajarilmadi"),
            show_alert=True,
        )
        return
    await callback.message.edit_text(
        "✅ <b>EFC xaridi bajarildi</b>\n\n"
        f"🪙 Olindi: <b>{money(data['efc_amount'])} EFC</b>\n"
        f"💵 Sarflandi: <b>{money(data['uzs_cost'])} so‘m</b>\n"
        f"🪙 Yangi EFC balans: <b>{money(data['efc_balance'])}</b>\n"
        f"💵 Yangi UZS balans: <b>{money(data['uzs_balance'])} so‘m</b>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="🛍 Magazinga qaytish", callback_data="shop:open")
        ]]),
    )
    await callback.answer("Xarid muvaffaqiyatli")


@router.callback_query(F.data == "shop:ticket")
async def shop_ticket_start(callback: CallbackQuery, state: FSMContext):
    try:
        payload = await get_shop_catalog(callback.from_user.id)
    except Exception:
        payload = None
    data = _catalog_data(payload or {})
    if data is None:
        await callback.answer(
            (payload or {}).get("message", "Magazin vaqtincha ishlamayapti"),
            show_alert=True,
        )
        return
    await state.set_state(ShopState.ticket_quantity)
    await state.update_data(
        ticket_price_efc=str(data["ticket_price_efc"]),
        max_tickets=int(data["max_tickets_per_purchase"]),
    )
    await callback.message.answer(
        "🎟 <b>Arena Ticket olish</b>\n\n"
        f"1 Ticket = {money(data['ticket_price_efc'])} EFC\n"
        f"EFC balans: {money(data['efc_balance'])} EFC\n\n"
        "Nechta Ticket olmoqchisiz?\n"
        "Masalan: <code>1</code>",
        reply_markup=cancel_keyboard(),
    )
    await callback.answer()


@router.message(ShopState.ticket_quantity)
async def shop_ticket_quote(message: Message, state: FSMContext):
    quantity = parse_ticket_quantity(message.text)
    state_data = await state.get_data()
    maximum = int(state_data.get("max_tickets", 0))
    if quantity is None or quantity > maximum:
        await message.answer(
            f"❌ 1 dan {maximum} gacha butun son kiriting."
        )
        return
    price = Decimal(state_data["ticket_price_efc"])
    cost = price * quantity
    await state.clear()
    await message.answer(
        "🧾 <b>Xaridni tasdiqlang</b>\n\n"
        f"🎟 Ticket: <b>{quantity}</b>\n"
        f"🪙 Narx: <b>{money(cost)} EFC</b>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="✅ Ticket olish",
                callback_data=f"shop:confirm:ticket:{quantity}",
            )],
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="shop:open")],
        ]),
    )


@router.callback_query(F.data.startswith("shop:confirm:ticket:"))
async def shop_ticket_confirm(callback: CallbackQuery):
    quantity = parse_ticket_quantity((callback.data or "").rsplit(":", 1)[-1])
    if quantity is None:
        await callback.answer("Ticket soni noto‘g‘ri", show_alert=True)
        return
    key = f"bot-shop-ticket:{callback.from_user.id}:{callback.message.message_id}"
    try:
        payload = await buy_shop_tickets(callback.from_user.id, quantity, key)
    except Exception:
        payload = None
    data = _catalog_data(payload or {})
    if data is None:
        await callback.answer(
            (payload or {}).get("message", "Xarid bajarilmadi"),
            show_alert=True,
        )
        return
    await callback.message.edit_text(
        "✅ <b>Ticket xaridi bajarildi</b>\n\n"
        f"🎟 Olindi: <b>{int(data['ticket_quantity'])} Ticket</b>\n"
        f"🪙 Sarflandi: <b>{money(data['efc_cost'])} EFC</b>\n"
        f"🎟 Yangi Ticket balans: <b>{int(data['ticket_balance'])}</b>\n"
        f"🪙 Yangi EFC balans: <b>{money(data['efc_balance'])} EFC</b>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="🛍 Magazinga qaytish", callback_data="shop:open")
        ]]),
    )
    await callback.answer("Xarid muvaffaqiyatli")
