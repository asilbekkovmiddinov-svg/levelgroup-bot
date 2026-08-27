from decimal import Decimal, InvalidOperation

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from config import ADMIN_CHAT_ID, ADMIN_USER_IDS
from services.api import get_shop_admin_settings, update_shop_admin_settings


router = Router()


class ShopAdminState(StatesGroup):
    efc_price = State()
    ticket_price = State()


def is_shop_admin(user_id: int) -> bool:
    value = int(user_id)
    return value in ADMIN_USER_IDS or (
        bool(ADMIN_CHAT_ID) and value == int(ADMIN_CHAT_ID)
    )


def parse_price(value: str) -> Decimal | None:
    normalized = str(value or "").replace(" ", "").replace(",", ".").strip()
    try:
        price = Decimal(normalized)
    except (InvalidOperation, ValueError):
        return None
    if price <= 0 or price.as_tuple().exponent < -2:
        return None
    return price


def price_text(value) -> str:
    if value is None:
        return "Belgilanmagan"
    try:
        return f"{Decimal(str(value)):,.2f}".replace(",", " ")
    except (InvalidOperation, ValueError):
        return "0.00"


def admin_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="✏️ Narxlarni belgilash",
            callback_data="shop_admin:set_prices",
        )],
        [InlineKeyboardButton(
            text="🔄 Yangilash",
            callback_data="shop_admin:open",
        )],
    ])


def cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="❌ Bekor qilish",
            callback_data="shop_admin:open",
        )
    ]])


def settings_data(payload: dict) -> dict | None:
    if not isinstance(payload, dict) or not payload.get("success"):
        return None
    data = payload.get("data")
    return data if isinstance(data, dict) else None


async def send_admin_settings(message: Message):
    try:
        payload = await get_shop_admin_settings()
    except Exception:
        payload = None
    data = settings_data(payload or {})
    if data is None:
        detail = (payload or {}).get("message") if isinstance(payload, dict) else None
        await message.answer(f"❌ Narxlar olinmadi. {detail or 'Qayta urinib ko‘ring.'}")
        return
    await message.answer(
        "🛠 <b>MAGAZIN NARXLARI</b>\n\n"
        f"💵 1 EFC = <b>{price_text(data['efc_price_uzs'])} so‘m</b>\n"
        f"🎟 1 Arena Ticket = <b>{price_text(data['ticket_price_efc'])} EFC</b>\n\n"
        "Magazin faqat ikkala narx belgilangandan keyin savdoni boshlaydi.",
        reply_markup=admin_keyboard(),
    )


@router.message(Command("shop_admin"))
async def shop_admin_command(message: Message, state: FSMContext):
    if not is_shop_admin(message.from_user.id):
        return
    await state.clear()
    await send_admin_settings(message)


@router.callback_query(F.data == "shop_admin:open")
async def shop_admin_open(callback: CallbackQuery, state: FSMContext):
    if not is_shop_admin(callback.from_user.id):
        await callback.answer("Ruxsat yo‘q", show_alert=True)
        return
    await state.clear()
    await callback.answer()
    await send_admin_settings(callback.message)


@router.callback_query(F.data == "shop_admin:set_prices")
async def shop_admin_efc_start(callback: CallbackQuery, state: FSMContext):
    if not is_shop_admin(callback.from_user.id):
        await callback.answer("Ruxsat yo‘q", show_alert=True)
        return
    await state.set_state(ShopAdminState.efc_price)
    await callback.message.answer(
        "💵 <b>Yangi EFC narxi</b>\n\n"
        "1 EFC necha so‘m bo‘lishini yozing.\n"
        "Masalan: <code>1000</code>",
        reply_markup=cancel_keyboard(),
    )
    await callback.answer()


@router.message(ShopAdminState.efc_price)
async def shop_admin_efc_save(message: Message, state: FSMContext):
    if not is_shop_admin(message.from_user.id):
        await state.clear()
        return
    price = parse_price(message.text)
    if price is None:
        await message.answer("❌ 0 dan katta, ko‘pi bilan 2 kasr xonali narx yozing.")
        return
    await state.update_data(efc_price_uzs=str(price))
    await state.set_state(ShopAdminState.ticket_price)
    await message.answer(
        "🎟 <b>Yangi Ticket narxi</b>\n\n"
        "1 Arena Ticket necha EFC bo‘lishini yozing.\n"
        "Masalan: <code>10</code>",
        reply_markup=cancel_keyboard(),
    )


@router.message(ShopAdminState.ticket_price)
async def shop_admin_ticket_save(message: Message, state: FSMContext):
    if not is_shop_admin(message.from_user.id):
        await state.clear()
        return
    price = parse_price(message.text)
    if price is None:
        await message.answer("❌ 0 dan katta, ko‘pi bilan 2 kasr xonali narx yozing.")
        return
    data = await state.get_data()
    payload = await update_shop_admin_settings(
        message.from_user.id,
        data["efc_price_uzs"],
        price,
    )
    result = settings_data(payload)
    if result is None:
        await message.answer(f"❌ {payload.get('message', 'Narx saqlanmadi')}")
        return
    await state.clear()
    await message.answer(
        "✅ <b>Magazin narxlari yangilandi</b>\n\n"
        f"💵 1 EFC = <b>{price_text(result['efc_price_uzs'])} so‘m</b>\n"
        f"🎟 1 Ticket = <b>{price_text(result['ticket_price_efc'])} EFC</b>",
        reply_markup=admin_keyboard(),
    )
