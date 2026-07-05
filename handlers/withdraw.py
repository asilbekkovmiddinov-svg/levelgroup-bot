from aiogram import Router, F
from aiogram.types import (
    CallbackQuery,
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from config import NEW_ORDERS_CHANNEL_ID
from services.api import create_withdraw

router = Router()

MIN_WITHDRAW_AMOUNT = 15000


class WithdrawState(StatesGroup):
    bank_name = State()
    card = State()
    full_name = State()
    amount = State()


def format_card(card: str):
    card = card.replace(" ", "")
    return " ".join(card[i:i + 4] for i in range(0, len(card), 4))


@router.callback_query(F.data == "withdraw_start")
async def withdraw_start(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.set_state(WithdrawState.bank_name)

    await callback.message.answer(
        "💸 UZS yechish\n\n"
        "Avval karta bank nomini kiriting.\n\n"
        "Masalan:\n"
        "Kapitalbank\n"
        "Ipak Yo‘li Bank\n"
        "Agrobank"
    )

    await callback.answer()


@router.message(WithdrawState.bank_name)
async def withdraw_bank_name(message: Message, state: FSMContext):
    bank_name = message.text.strip()

    if len(bank_name) < 2:
        await message.answer("❌ Bank nomini to‘liq kiriting.")
        return

    await state.update_data(bank_name=bank_name)
    await state.set_state(WithdrawState.card)

    await message.answer(
        "💳 Pul yuboriladigan karta raqamini kiriting.\n\n"
        "Masalan:\n"
        "8600 0000 0000 0000"
    )


@router.message(WithdrawState.card)
async def withdraw_card(message: Message, state: FSMContext):
    card = message.text.replace(" ", "")

    if not card.isdigit():
        await message.answer(
            "❌ Karta raqam faqat raqamlardan iborat bo‘lishi kerak."
        )
        return

    if len(card) != 16:
        await message.answer(
            "❌ Karta raqam 16 ta raqamdan iborat bo‘lishi kerak."
        )
        return

    await state.update_data(card=card)
    await state.set_state(WithdrawState.full_name)

    await message.answer(
        "👤 Karta egasining ism familiyasini kiriting.\n\n"
        "Masalan:\n"
        "Aliyev Ali"
    )
@router.message(WithdrawState.full_name)
async def withdraw_full_name(message: Message, state: FSMContext):
    full_name = message.text.strip()

    if len(full_name) < 3:
        await message.answer("❌ Ism familiyani to‘liq kiriting.")
        return

    await state.update_data(full_name=full_name)
    await state.set_state(WithdrawState.amount)

    await message.answer(
        "💵 Yechib olmoqchi bo‘lgan summani kiriting.\n\n"
        f"Minimal summa: {MIN_WITHDRAW_AMOUNT:,} so‘m\n\n"
        "Masalan: 50000"
    )


@router.message(WithdrawState.amount)
async def withdraw_amount(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("❌ Faqat raqam kiriting. Masalan: 50000")
        return

    amount = int(message.text)

    if amount < MIN_WITHDRAW_AMOUNT:
        await message.answer(
            f"❌ Minimal yechish summasi {MIN_WITHDRAW_AMOUNT:,} so‘m.\n\n"
            f"Iltimos, {MIN_WITHDRAW_AMOUNT:,} yoki undan yuqori summa kiriting."
        )
        return

    data = await state.get_data()
    bank_name = data["bank_name"]
    card = data["card"]
    full_name = data["full_name"]
    formatted_card = format_card(card)

    await message.answer("⏳ So‘rovingiz yuborilmoqda...")

    try:
        result = await create_withdraw(
            telegram_id=message.from_user.id,
            amount=amount,
            card_number=formatted_card,
            card_holder=full_name,
            bank_name=bank_name,
        )
    except Exception:
        await message.answer("❌ Backend bilan aloqa qilishda xatolik yuz berdi.")
        await state.clear()
        return

    if not result:
        await message.answer("❌ Serverdan javob kelmadi. Qayta urinib ko‘ring.")
        await state.clear()
        return

    if result.get("message") == "Balans yetarli emas":
        await message.answer(
            "❌ Balansingiz yetarli emas.\n\n"
            f"💵 So‘ralgan summa: {amount:,} so‘m"
        )
        await state.clear()
        return

    if "withdraw_id" not in result:
        await message.answer(
            "❌ Xatolik yuz berdi.\n\n"
            f"Server javobi: {result.get('message', 'Nomaʼlum xatolik')}"
        )
        await state.clear()
        return

    withdraw_id = result["withdraw_id"]

    username = (
        f"@{message.from_user.username}"
        if message.from_user.username
        else message.from_user.first_name
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🙋 Qabul qilish",
                    callback_data=f"claim_withdraw_{withdraw_id}",
                )
            ]
        ]
    )

    await message.bot.send_message(
        chat_id=NEW_ORDERS_CHANNEL_ID,
        text=(
            "💸 YANGI WITHDRAW\n\n"
            f"🆔 Buyurtma: #{withdraw_id}\n\n"
            f"👤 Mijoz: {username}\n"
            f"🆔 Telegram ID: {message.from_user.id}\n\n"
            "🎮 Xizmat: UZS yechish\n"
            f"💵 Summa: {amount:,} so‘m\n"
            f"🏦 Bank: {bank_name}\n"
            f"💳 Karta: {formatted_card}\n"
            f"👤 Karta egasi: {full_name}\n\n"
            "⏳ Muddat: 24 soatgacha\n"
            "📌 Status: PENDING\n\n"
            "👇 Adminlardan biri qabul qilsin."
        ),
        reply_markup=keyboard,
    )

    await state.clear()

    await message.answer(
        "✅ Pul yechish so‘rovingiz qabul qilindi!\n\n"
        f"🆔 Buyurtma: #{withdraw_id}\n"
        f"💵 Summa: {amount:,} so‘m\n"
        f"🏦 Bank: {bank_name}\n"
        f"💳 Karta: {formatted_card}\n"
        f"👤 Karta egasi: {full_name}\n\n"
        "⏳ To‘lov 24 soat ichida kartangizga yuboriladi."
    )
