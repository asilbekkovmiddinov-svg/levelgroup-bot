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
    reserve_p2p_order,
    complete_p2p_order,
    cancel_p2p_order,
)

router = Router()

MIN_P2P_EFC = 1
MIN_P2P_UZS = 1000


class P2PState(StatesGroup):
    efc_amount = State()
    price_uzs = State()


def p2p_menu_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📋 E'lonlar",
                    callback_data="p2p_open_orders",
                )
            ],
            [
                InlineKeyboardButton(
                    text="💰 EFC sotish",
                    callback_data="p2p_sell_start",
                )
            ],
        ]
    )


@router.message(F.text == "🤝 P2P Market")
async def p2p_menu(message: Message):
    await message.answer(
        "🤝 P2P Market\n\n"
        "Bu yerda foydalanuvchilar EFC sotishi va sotib olishi mumkin.\n\n"
        "Komissiya:\n"
        "• Sotuvchi: 2.5% EFC\n"
        "• Xaridor: 2.5% UZS\n\n"
        "Kerakli bo‘limni tanlang:",
        reply_markup=p2p_menu_keyboard(),
    )


@router.callback_query(F.data == "p2p_menu")
async def p2p_menu_callback(callback: CallbackQuery):
    await callback.message.answer(
        "🤝 P2P Market\n\n"
        "Kerakli bo‘limni tanlang:",
        reply_markup=p2p_menu_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "p2p_sell_start")
async def p2p_sell_start(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.set_state(P2PState.efc_amount)

    await callback.message.answer(
        "💰 EFC sotish\n\n"
        "Sotmoqchi bo‘lgan EFC miqdorini kiriting.\n\n"
        f"Minimal: {MIN_P2P_EFC} EFC\n"
        "Masalan: 10"
    )

    await callback.answer()
@router.message(P2PState.efc_amount)
async def p2p_efc_amount(message: Message, state: FSMContext):
    try:
        efc_amount = float(message.text.replace(",", "."))
    except Exception:
        await message.answer("❌ Faqat raqam kiriting. Masalan: 10")
        return

    if efc_amount < MIN_P2P_EFC:
        await message.answer(
            f"❌ Minimal sotish miqdori {MIN_P2P_EFC} EFC."
        )
        return

    await state.update_data(efc_amount=efc_amount)
    await state.set_state(P2PState.price_uzs)

    await message.answer(
        "💵 EFC uchun UZS narxini kiriting.\n\n"
        "Masalan:\n"
        "10000\n\n"
        "Bu xaridor to‘laydigan asosiy narx bo‘ladi."
    )


@router.message(P2PState.price_uzs)
async def p2p_price_uzs(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("❌ Faqat raqam kiriting. Masalan: 10000")
        return

    price_uzs = int(message.text)

    if price_uzs < MIN_P2P_UZS:
        await message.answer(
            f"❌ Minimal narx {MIN_P2P_UZS:,} so‘m."
        )
        return

    data = await state.get_data()
    efc_amount = data["efc_amount"]

    result = await create_p2p_order(
        telegram_id=message.from_user.id,
        efc_amount=efc_amount,
        price_uzs=price_uzs,
    )

    if result.get("message") == "EFC balans yetarli emas":
        await message.answer(
            "❌ EFC balansingiz yetarli emas.\n\n"
            f"🪙 Kerakli EFC: {efc_amount}"
        )
        await state.clear()
        return

    if result.get("message") != "P2P order yaratildi":
        await message.answer(
            "❌ P2P e'lon yaratishda xatolik.\n\n"
            f"Server javobi: {result.get('message', 'Nomaʼlum xatolik')}"
        )
        await state.clear()
        return

    await state.clear()

    await message.answer(
        "✅ P2P e'lon yaratildi!\n\n"
        f"🆔 Order: #{result.get('id')}\n"
        f"🪙 EFC: {result.get('efc_amount')}\n"
        f"💵 Narx: {int(result.get('price_uzs', 0)):,} so‘m\n"
        f"🔥 EFC komissiya: {result.get('seller_fee_efc')} EFC\n"
        f"💰 Siz olasiz: {int(result.get('seller_receive_uzs', 0)):,} so‘m\n\n"
        "E'loningiz P2P Marketda ko‘rinadi.",
        reply_markup=p2p_menu_keyboard(),
    )
@router.callback_query(F.data == "p2p_open_orders")
async def p2p_open_orders(callback: CallbackQuery):
    orders = await get_open_p2p_orders()

    if not orders:
        await callback.message.answer(
            "📋 Hozircha ochiq P2P e'lonlar yo‘q.",
            reply_markup=p2p_menu_keyboard(),
        )
        await callback.answer()
        return

    for order in orders[:10]:
        order_id = order.get("id")
        efc_amount = order.get("efc_amount", 0)
        price_uzs = int(order.get("price_uzs", 0))
        buyer_fee = int(order.get("buyer_fee_uzs", 0))
        total_pay = int(order.get("total_buyer_pay_uzs", 0))

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🛒 Sotib olish",
                        callback_data=f"p2p_buy_{order_id}",
                    )
                ]
            ]
        )

        await callback.message.answer(
            "📋 P2P E'LON\n\n"
            f"🆔 Order: #{order_id}\n"
            f"🪙 EFC: {efc_amount}\n"
            f"💵 Narx: {price_uzs:,} so‘m\n"
            f"➕ Xaridor komissiyasi: {buyer_fee:,} so‘m\n"
            f"💳 Jami to‘lov: {total_pay:,} so‘m\n\n"
            "👇 Sotib olish uchun tugmani bosing.",
            reply_markup=keyboard,
        )

    await callback.answer()


@router.callback_query(F.data.startswith("p2p_buy_"))
async def p2p_buy(callback: CallbackQuery):
    order_id = int(callback.data.replace("p2p_buy_", ""))

    result = await reserve_p2p_order(
        order_id=order_id,
        telegram_id=callback.from_user.id,
    )

    if result.get("message") == "O‘zingizning orderingizni sotib olmaysiz":
        await callback.answer(
            "❌ O‘zingizning e'loningizni sotib olmaysiz.",
            show_alert=True,
        )
        return

    if result.get("message") == "Order ochiq emas":
        await callback.answer(
            "❌ Bu e'lon allaqachon band qilingan yoki yopilgan.",
            show_alert=True,
        )
        return

    if result.get("message") != "P2P order band qilindi":
        await callback.answer(
            f"❌ Xatolik: {result.get('message', 'Nomaʼlum')}",
            show_alert=True,
        )
        return

    order_id = result.get("id")
    efc_amount = result.get("efc_amount")
    total_pay = int(result.get("total_buyer_pay_uzs", 0))
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Sotib olishni yakunlash",
                    callback_data=f"p2p_complete_{order_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Bekor qilish",
                    callback_data=f"p2p_cancel_{order_id}",
                )
            ],
        ]
    )

    await callback.message.answer(
        "✅ P2P e'lon band qilindi!\n\n"
        f"🆔 Order: #{order_id}\n"
        f"🪙 EFC: {efc_amount}\n"
        f"💳 Jami to‘lov: {total_pay:,} so‘m\n\n"
        "Davom etish uchun sotib olishni yakunlang.",
        reply_markup=keyboard,
    )

    await callback.answer("✅ Order band qilindi.")


@router.callback_query(F.data.startswith("p2p_complete_"))
async def p2p_complete(callback: CallbackQuery):
    order_id = int(callback.data.replace("p2p_complete_", ""))

    result = await complete_p2p_order(
        order_id=order_id,
        telegram_id=callback.from_user.id,
    )

    if result.get("message") == "UZS balans yetarli emas":
        await callback.answer(
            "❌ UZS balansingiz yetarli emas.",
            show_alert=True,
        )
        return

    if result.get("message") != "P2P order yakunlandi":
        await callback.answer(
            f"❌ Xatolik: {result.get('message', 'Nomaʼlum')}",
            show_alert=True,
        )
        return

    await callback.message.edit_text(
        "✅ P2P savdo yakunlandi!\n\n"
        f"🆔 Order: #{result.get('id')}\n"
        f"🪙 EFC: {result.get('efc_amount')}\n"
        f"💵 Narx: {int(result.get('price_uzs', 0)):,} so‘m\n\n"
        "EFC xaridor balansiga o‘tkazildi.\n"
        "UZS sotuvchi balansiga o‘tkazildi.\n\n"
        "🔥 LEVEL_GROUP"
    )

    await callback.answer("✅ Savdo yakunlandi.")


@router.callback_query(F.data.startswith("p2p_cancel_"))
async def p2p_cancel(callback: CallbackQuery):
    order_id = int(callback.data.replace("p2p_cancel_", ""))

    result = await cancel_p2p_order(
        order_id=order_id,
        telegram_id=callback.from_user.id,
    )

    if result.get("message") == "Faqat sotuvchi bekor qila oladi":
        await callback.answer(
            "❌ Faqat sotuvchi e'lonni bekor qila oladi.",
            show_alert=True,
        )
        return

    if result.get("message") != "P2P order bekor qilindi":
        await callback.answer(
            f"❌ Xatolik: {result.get('message', 'Nomaʼlum')}",
            show_alert=True,
        )
        return

    await callback.message.edit_text(
        "❌ P2P order bekor qilindi.\n\n"
        f"🆔 Order: #{result.get('id')}\n"
        "Bloklangan EFC sotuvchi balansiga qaytarildi."
    )

    await callback.answer("❌ Order bekor qilindi.")
