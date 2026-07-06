from aiogram import Router, F
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from config import ADMIN_CHAT_ID
from services.api import (
    get_wheel_status,
    spin_wheel,
    fill_wheel_coin_order,
)

router = Router()


class WheelCoinOrderState(StatesGroup):
    konami_login = State()
    konami_password = State()
    region = State()
    device = State()


def is_success(result):
    return isinstance(result, dict) and result.get("success") is True


def format_number(value):
    try:
        number = float(value)
    except Exception:
        return str(value)

    if number.is_integer():
        return f"{int(number):,}"

    return f"{number:,.2f}"


def wheel_menu_keyboard(status=None):
    buttons = [
        [
            InlineKeyboardButton(
                text="🎁 Bepul aylantirish",
                callback_data="wheel_spin_FREE",
            )
        ],
        [
            InlineKeyboardButton(
                text="📺 Reklama orqali aylantirish",
                callback_data="wheel_spin_AD",
            )
        ],
        [
            InlineKeyboardButton(
                text="🍀 Bonus spin",
                callback_data="wheel_spin_BONUS",
            )
        ],
        [
            InlineKeyboardButton(
                text="🔄 Yangilash",
                callback_data="wheel_menu",
            )
        ],
    ]

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def device_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🤖 Android",
                    callback_data="wheel_device_ANDROID",
                ),
                InlineKeyboardButton(
                    text="🍎 iOS",
                    callback_data="wheel_device_IOS",
                ),
            ]
        ]
    )


def get_status_text(status):
    free_text = "✅ ishlatilgan" if status.get("free_spin_used") else "🎁 tayyor"
    ad_count = status.get("ad_spin_count", 0)
    max_ad = status.get("max_ad_spins", 10)
    bonus_count = status.get("bonus_spin_count", 0)

    return (
        "🎰 LEVEL_GROUP Wheel\n\n"
        f"🎁 Bepul spin: {free_text}\n"
        f"📺 Reklama spin: {ad_count}/{max_ad}\n"
        f"🍀 Bonus spin: {bonus_count}\n\n"
        "Yutuqlar:\n"
        "🪙 5 / 10 / 25 / 50 / 100 / 250 EFC\n"
        "🏆 130 coin\n"
        "👑 2000 coin Jackpot\n"
        "🎁 Yana 1 marta bepul spin\n"
        "❌ Yutqazish"
    )
@router.message(F.text == "🎰 Wheel")
async def wheel_menu(message: Message):
    status = await get_wheel_status(message.from_user.id)

    if not is_success(status):
        await message.answer("❌ Wheel holatini olishda xatolik.")
        return

    await message.answer(
        get_status_text(status),
        reply_markup=wheel_menu_keyboard(status),
    )


@router.callback_query(F.data == "wheel_menu")
async def wheel_menu_callback(callback: CallbackQuery):
    status = await get_wheel_status(callback.from_user.id)

    if not is_success(status):
        await callback.answer("Wheel xatolik.", show_alert=True)
        return

    await callback.message.answer(
        get_status_text(status),
        reply_markup=wheel_menu_keyboard(status),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("wheel_spin_"))
async def wheel_spin_handler(callback: CallbackQuery, state: FSMContext):
    spin_type = callback.data.replace("wheel_spin_", "")

    result = await spin_wheel(
        telegram_id=callback.from_user.id,
        spin_type=spin_type,
    )

    if not is_success(result):
        await callback.answer(
            result.get("message", "Aylantirishda xatolik"),
            show_alert=True,
        )
        return

    reward_type = result.get("reward_type")
    reward_amount = result.get("reward_amount")
    reward_code = result.get("reward_code")
    spin_id = result.get("spin_id")

    text = (
        "🎰 Wheel aylantirildi!\n\n"
        f"{result.get('message')}\n\n"
    )

    if reward_type == "EFC":
        text += f"✅ Balansingizga {format_number(reward_amount)} EFC qo‘shildi."

    elif reward_type == "BONUS_SPIN":
        text += "🍀 Bonus spin hisobingizga qo‘shildi."

    elif reward_type == "COIN_ORDER":
        text += (
            f"🏆 Siz {format_number(reward_amount)} coin yutdingiz!\n\n"
            "Yutuqni olish uchun My Konami ma’lumotlarini kiriting."
        )

        await state.update_data(
            wheel_spin_id=spin_id,
            coin_amount=reward_amount,
            reward_code=reward_code,
        )
        await state.set_state(WheelCoinOrderState.konami_login)

        await callback.message.answer(text)
        await callback.message.answer(
            "🔐 My Konami loginni kiriting:"
        )
        await callback.answer()
        return

    else:
        text += "Keyingi safar omad!"

    await callback.message.answer(
        text,
        reply_markup=wheel_menu_keyboard(result),
    )
    await callback.answer()
@router.message(WheelCoinOrderState.konami_login)
async def wheel_coin_login(message: Message, state: FSMContext):
    login = message.text.strip()

    if len(login) < 3:
        await message.answer("❌ Login juda qisqa. Qayta kiriting.")
        return

    await state.update_data(konami_login=login)
    await state.set_state(WheelCoinOrderState.konami_password)

    await message.answer("🔑 My Konami parolni kiriting:")


@router.message(WheelCoinOrderState.konami_password)
async def wheel_coin_password(message: Message, state: FSMContext):
    password = message.text.strip()

    if len(password) < 3:
        await message.answer("❌ Parol juda qisqa. Qayta kiriting.")
        return

    await state.update_data(konami_password=password)
    await state.set_state(WheelCoinOrderState.region)

    await message.answer(
        "🌍 Regionni kiriting.\n\n"
        "Masalan: Turkey, Uzbekistan, Singapore"
    )


@router.message(WheelCoinOrderState.region)
async def wheel_coin_region(message: Message, state: FSMContext):
    region = message.text.strip()

    if len(region) < 2:
        await message.answer("❌ Region noto‘g‘ri. Qayta kiriting.")
        return

    await state.update_data(region=region)
    await state.set_state(WheelCoinOrderState.device)

    await message.answer(
        "📱 Qurilma turini tanlang:",
        reply_markup=device_keyboard(),
    )


@router.callback_query(F.data.startswith("wheel_device_"))
async def wheel_coin_device(callback: CallbackQuery, state: FSMContext):
    device = callback.data.replace("wheel_device_", "")

    if device not in ["ANDROID", "IOS"]:
        await callback.answer("Noto‘g‘ri qurilma.", show_alert=True)
        return

    data = await state.get_data()

    result = await fill_wheel_coin_order(
        telegram_id=callback.from_user.id,
        spin_id=data["wheel_spin_id"],
        konami_login=data["konami_login"],
        konami_password=data["konami_password"],
        region=data["region"],
        device=device,
    )

    if not is_success(result):
        await callback.answer(
            result.get("message", "Buyurtma yuborilmadi"),
            show_alert=True,
        )
        return

    await state.clear()

    coin_amount = data.get("coin_amount")
    username = callback.from_user.username or "username yo‘q"
    first_name = callback.from_user.first_name or "Ism yo‘q"
    admin_text = (
        "🏆 WHEEL COIN BUYURTMA\n\n"
        f"👤 Foydalanuvchi: {first_name}\n"
        f"🔗 Username: @{username}\n"
        f"🆔 Telegram ID: {callback.from_user.id}\n"
        f"🪙 Coin: {format_number(coin_amount)} coin\n\n"
        f"🔐 Login: {data['konami_login']}\n"
        f"🔑 Parol: {data['konami_password']}\n"
        f"🌍 Region: {data['region']}\n"
        f"📱 Qurilma: {device}\n\n"
        "Admin buyurtmani bajarishi kerak."
    )

    if ADMIN_CHAT_ID:
        try:
            await callback.bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text=admin_text,
            )
        except Exception:
            pass

    await callback.message.answer(
        "✅ Coin buyurtmangiz adminga yuborildi!\n\n"
        f"🪙 Yutuq: {format_number(coin_amount)} coin\n"
        "Admin buyurtmani tekshiradi va bajaradi."
    )

    await callback.answer("Buyurtma yuborildi.")


@router.callback_query(F.data == "wheel_help")
async def wheel_help(callback: CallbackQuery):
    await callback.message.answer(
        "🎰 Wheel qoidalari\n\n"
        "🎁 Kuniga 1 ta bepul spin.\n"
        "📺 Har 1 soatda reklama orqali spin.\n"
        "🔒 Kuniga maksimum 10 ta reklama spini.\n"
        "🍀 Bonus spin yutuqdan chiqadi.\n\n"
        "EFC yutuqlari avtomatik balansga tushadi.\n"
        "130 coin va 2000 coin yutuqlari admin orqali bajariladi."
    )
    await callback.answer()


@router.message(F.text == "🎡 Wheel")
async def wheel_menu_alt(message: Message):
    await wheel_menu(message)


@router.message(F.text == "Wheel")
async def wheel_menu_text(message: Message):
    await wheel_menu(message)
@router.message(F.text == "🎁 Bepul aylantirish")
async def wheel_free_text(message: Message):
    result = await spin_wheel(
        telegram_id=message.from_user.id,
        spin_type="FREE",
    )

    if not is_success(result):
        await message.answer(result.get("message", "Xatolik"))
        return

    await message.answer(
        "🎰 Natija:\n\n"
        f"{result.get('message')}",
        reply_markup=wheel_menu_keyboard(result),
    )


@router.message(F.text == "📺 Reklama aylantirish")
async def wheel_ad_text(message: Message):
    result = await spin_wheel(
        telegram_id=message.from_user.id,
        spin_type="AD",
    )

    if not is_success(result):
        await message.answer(result.get("message", "Xatolik"))
        return

    await message.answer(
        "🎰 Natija:\n\n"
        f"{result.get('message')}",
        reply_markup=wheel_menu_keyboard(result),
    )


@router.message(F.text == "🍀 Bonus aylantirish")
async def wheel_bonus_text(message: Message):
    result = await spin_wheel(
        telegram_id=message.from_user.id,
        spin_type="BONUS",
    )

    if not is_success(result):
        await message.answer(result.get("message", "Xatolik"))
        return

    await message.answer(
        "🎰 Natija:\n\n"
        f"{result.get('message')}",
        reply_markup=wheel_menu_keyboard(result),
    )
@router.message(F.text == "🎰 Baraban")
async def wheel_menu_baraban(message: Message):
    await wheel_menu(message)


@router.message(F.text == "🎡 Baraban")
async def wheel_menu_baraban_alt(message: Message):
    await wheel_menu(message)


@router.message(F.text == "Baraban")
async def wheel_menu_baraban_text(message: Message):
    await wheel_menu(message)
