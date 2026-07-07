from datetime import datetime

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from services.match_api import (
    accept_match,
    create_match,
    create_room_code,
    get_leaderboard,
    get_match,
    get_match_guide,
    get_open_matches,
    get_user_matches,
    set_player_ready,
    upload_result_screenshot,
)

router = Router()


class MatchCreateState(StatesGroup):
    efc_amount = State()
    scheduled_at = State()


class MatchRoomCodeState(StatesGroup):
    room_code = State()


class MatchScreenshotState(StatesGroup):
    screenshot = State()


def arena_menu_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🎮 Match yaratish",
                    callback_data="arena_create",
                )
            ],
            [
                InlineKeyboardButton(
                    text="📋 Ochiq matchlar",
                    callback_data="arena_open",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🕹 Mening matchlarim",
                    callback_data="arena_my_matches",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🏆 Match reytinglari",
                    callback_data="arena_ratings",
                )
            ],
            [
                InlineKeyboardButton(
                    text="📘 1vs1 qo‘llanma",
                    callback_data="arena_guide",
                )
            ],
        ]
    )


def back_to_arena_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⬅️ Arena menyu",
                    callback_data="arena_menu",
                )
            ]
        ]
    )


def match_action_keyboard(match_id: int, status: str):
    buttons = []

    if status == "WAITING_PLAYER":
        buttons.append(
            [
                InlineKeyboardButton(
                    text="✅ Matchni qabul qilish",
                    callback_data=f"arena_accept:{match_id}",
                )
            ]
        )

    if status == "READY_CHECK":
        buttons.append(
            [
                InlineKeyboardButton(
                    text="✅ Men tayyorman",
                    callback_data=f"arena_ready:{match_id}",
                )
            ]
        )

    if status == "WAITING_ROOM_CODE":
        buttons.append(
            [
                InlineKeyboardButton(
                    text="🔐 Room Code yozish",
                    callback_data=f"arena_room_code:{match_id}",
                )
            ]
        )

    if status in ["ROOM_CREATED", "MATCH_STARTED"]:
        buttons.append(
            [
                InlineKeyboardButton(
                    text="📸 Natija screenshot yuborish",
                    callback_data=f"arena_screenshot:{match_id}",
                )
            ]
        )

    buttons.append(
        [
            InlineKeyboardButton(
                text="⬅️ Arena menyu",
                callback_data="arena_menu",
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def format_match(match: dict) -> str:
    opponent = match.get("opponent_telegram_id") or "hali yo‘q"
    room_code = match.get("room_code") or "hali yo‘q"

    return (
        f"🎮 <b>1vs1 Arena Match</b>\n\n"
        f"🆔 Match ID: <code>{match['id']}</code>\n"
        f"👤 Yaratuvchi: <code>{match['creator_telegram_id']}</code>\n"
        f"👥 Raqib: <code>{opponent}</code>\n"
        f"💰 Tikilgan EFC: <b>{match['efc_amount']}</b>\n"
        f"🏆 G‘olib mukofoti: <b>{match['winner_reward']}</b>\n"
        f"📌 Status: <b>{match['status']}</b>\n"
        f"🕒 Boshlanish vaqti: <code>{match['scheduled_at']}</code>\n"
        f"🔐 Room Code: <code>{room_code}</code>"
    )


@router.message(F.text.in_(["🎮 1vs1 Arena", "1vs1 Arena", "/arena"]))
async def arena_menu_message(message: Message):
    await message.answer(
        "🎮 <b>1vs1 Arena</b>\n\n"
        "Bu yerda EFC tikib boshqa foydalanuvchi bilan 1vs1 match o‘ynaysiz.",
        reply_markup=arena_menu_keyboard(),
    )


@router.callback_query(F.data == "arena_menu")
async def arena_menu_callback(callback: CallbackQuery):
    await callback.message.edit_text(
        "🎮 <b>1vs1 Arena</b>\n\n"
        "Kerakli bo‘limni tanlang.",
        reply_markup=arena_menu_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "arena_create")
async def arena_create_start(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.set_state(MatchCreateState.efc_amount)

    await callback.message.edit_text(
        "💰 Match uchun EFC miqdorini yozing.\n\n"
        "Masalan: <code>100</code>",
        reply_markup=back_to_arena_keyboard(),
    )
    await callback.answer()


@router.message(MatchCreateState.efc_amount)
async def arena_create_amount(message: Message, state: FSMContext):
    try:
        efc_amount = float(message.text.replace(",", "."))
    except ValueError:
        await message.answer("❌ EFC miqdorini faqat raqam bilan yozing.")
        return

    if efc_amount <= 0:
        await message.answer("❌ EFC miqdori 0 dan katta bo‘lishi kerak.")
        return

    await state.update_data(efc_amount=efc_amount)
    await state.set_state(MatchCreateState.scheduled_at)

    await message.answer(
        "🕒 Match boshlanish vaqtini yozing.\n\n"
        "Format:\n"
        "<code>2026-07-07 21:30</code>\n\n"
        "Vaqtni shu formatda yuboring."
    )


@router.message(MatchCreateState.scheduled_at)
async def arena_create_time(message: Message, state: FSMContext):
    try:
        scheduled_at = datetime.strptime(message.text.strip(), "%Y-%m-%d %H:%M")
    except ValueError:
        await message.answer(
            "❌ Vaqt formati xato.\n\n"
            "To‘g‘ri format:\n"
            "<code>2026-07-07 21:30</code>"
        )
        return

    data = await state.get_data()
    efc_amount = data["efc_amount"]

    try:
        match = await create_match(
            creator_telegram_id=message.from_user.id,
            efc_amount=efc_amount,
            scheduled_at=scheduled_at.isoformat(),
        )
    except ValueError as error:
        await message.answer(f"❌ {error}")
        return

    await state.clear()

    await message.answer(
        "✅ Match e’loni yaratildi!\n\n"
        f"{format_match(match)}",
        reply_markup=match_action_keyboard(match["id"], match["status"]),
  )


@router.callback_query(F.data == "arena_open")
async def arena_open_matches(callback: CallbackQuery):
    try:
        data = await get_open_matches()
        matches = data.get("matches", [])
    except ValueError as error:
        await callback.message.edit_text(
            f"❌ {error}",
            reply_markup=back_to_arena_keyboard(),
        )
        await callback.answer()
        return

    if not matches:
        await callback.message.edit_text(
            "📋 Hozircha ochiq matchlar yo‘q.",
            reply_markup=back_to_arena_keyboard(),
        )
        await callback.answer()
        return

    text = "📋 <b>Ochiq matchlar</b>\n\n"
    keyboard = []

    for match in matches[:10]:
        text += (
            f"🆔 <code>{match['id']}</code> | "
            f"💰 {match['efc_amount']} EFC | "
            f"🕒 {match['scheduled_at']}\n"
        )
        keyboard.append(
            [
                InlineKeyboardButton(
                    text=f"✅ Qabul qilish #{match['id']}",
                    callback_data=f"arena_accept:{match['id']}",
                )
            ]
        )

    keyboard.append(
        [
            InlineKeyboardButton(
                text="⬅️ Arena menyu",
                callback_data="arena_menu",
            )
        ]
    )

    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("arena_accept:"))
async def arena_accept_match(callback: CallbackQuery):
    match_id = int(callback.data.split(":")[1])

    try:
        match = await accept_match(
            match_id=match_id,
            opponent_telegram_id=callback.from_user.id,
        )
    except ValueError as error:
        await callback.message.edit_text(
            f"❌ {error}",
            reply_markup=back_to_arena_keyboard(),
        )
        await callback.answer()
        return

    await callback.message.edit_text(
        "✅ Match qabul qilindi!\n\n"
        f"{format_match(match)}",
        reply_markup=match_action_keyboard(match["id"], match["status"]),
    )
    await callback.answer()


@router.callback_query(F.data == "arena_my_matches")
async def arena_my_matches(callback: CallbackQuery):
    try:
        data = await get_user_matches(callback.from_user.id)
        matches = data.get("matches", [])
    except ValueError as error:
        await callback.message.edit_text(
            f"❌ {error}",
            reply_markup=back_to_arena_keyboard(),
        )
        await callback.answer()
        return

    if not matches:
        await callback.message.edit_text(
            "🕹 Sizda hali matchlar yo‘q.",
            reply_markup=back_to_arena_keyboard(),
        )
        await callback.answer()
        return

    text = "🕹 <b>Mening matchlarim</b>\n\n"
    keyboard = []

    for match in matches[:10]:
        text += (
            f"🆔 <code>{match['id']}</code> | "
            f"💰 {match['efc_amount']} EFC | "
            f"📌 {match['status']}\n"
        )
        keyboard.append(
            [
                InlineKeyboardButton(
                    text=f"👁 Match #{match['id']}",
                    callback_data=f"arena_view:{match['id']}",
                )
            ]
        )

    keyboard.append(
        [
            InlineKeyboardButton(
                text="⬅️ Arena menyu",
                callback_data="arena_menu",
            )
        ]
    )

    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("arena_view:"))
async def arena_view_match(callback: CallbackQuery):
    match_id = int(callback.data.split(":")[1])

    try:
        match = await get_match(match_id)
    except ValueError as error:
        await callback.message.edit_text(
            f"❌ {error}",
            reply_markup=back_to_arena_keyboard(),
        )
        await callback.answer()
        return

    await callback.message.edit_text(
        format_match(match),
        reply_markup=match_action_keyboard(match["id"], match["status"]),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("arena_ready:"))
async def arena_ready(callback: CallbackQuery):
    match_id = int(callback.data.split(":")[1])

    try:
        match = await set_player_ready(
            match_id=match_id,
            telegram_id=callback.from_user.id,
        )
    except ValueError as error:
        await callback.message.edit_text(
            f"❌ {error}",
            reply_markup=back_to_arena_keyboard(),
        )
        await callback.answer()
        return

    await callback.message.edit_text(
        "✅ Tayyor holatingiz qabul qilindi!\n\n"
        f"{format_match(match)}",
        reply_markup=match_action_keyboard(match["id"], match["status"]),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("arena_room_code:"))
async def arena_room_code_start(callback: CallbackQuery, state: FSMContext):
    match_id = int(callback.data.split(":")[1])

    await state.clear()
    await state.set_state(MatchRoomCodeState.room_code)
    await state.update_data(match_id=match_id)

    await callback.message.edit_text(
        "🔐 Room Code yozing.\n\n"
        "Eslatma: Room Code faqat bir marta yoziladi, keyin o‘zgartirib bo‘lmaydi.",
        reply_markup=back_to_arena_keyboard(),
    )
    await callback.answer()


@router.message(MatchRoomCodeState.room_code)
async def arena_room_code_save(message: Message, state: FSMContext):
    data = await state.get_data()
    match_id = data["match_id"]

    try:
        match = await create_room_code(
            match_id=match_id,
            telegram_id=message.from_user.id,
            room_code=message.text,
        )
    except ValueError as error:
        await message.answer(f"❌ {error}")
        return

    await state.clear()

    await message.answer(
        "✅ Room Code saqlandi!\n\n"
        f"{format_match(match)}",
        reply_markup=match_action_keyboard(match["id"], match["status"]),
    )


@router.callback_query(F.data.startswith("arena_screenshot:"))
async def arena_screenshot_start(callback: CallbackQuery, state: FSMContext):
    match_id = int(callback.data.split(":")[1])

    await state.clear()
    await state.set_state(MatchScreenshotState.screenshot)
    await state.update_data(match_id=match_id)

    await callback.message.edit_text(
        "📸 O‘yin natijasi screenshotini yuboring.\n\n"
        "Faqat rasm yuboring.",
        reply_markup=back_to_arena_keyboard(),
    )
    await callback.answer()


@router.message(MatchScreenshotState.screenshot, F.photo)
async def arena_screenshot_save(message: Message, state: FSMContext):
    data = await state.get_data()
    match_id = data["match_id"]

    photo = message.photo[-1]
    screenshot_file_id = photo.file_id

    try:
        match = await upload_result_screenshot(
            match_id=match_id,
            telegram_id=message.from_user.id,
            screenshot_file_id=screenshot_file_id,
        )
    except ValueError as error:
        await message.answer(f"❌ {error}")
        return

    await state.clear()

    await message.answer(
        "✅ Screenshot qabul qilindi.\n\n"
        "Admin natijani tekshiradi va matchni yakunlaydi.",
        reply_markup=match_action_keyboard(match["id"], match["status"]),
    )


@router.message(MatchScreenshotState.screenshot)
async def arena_screenshot_wrong(message: Message):
    await message.answer("❌ Iltimos, faqat screenshot rasm yuboring.")


@router.callback_query(F.data == "arena_ratings")
async def arena_ratings(callback: CallbackQuery):
    try:
        data = await get_leaderboard(period="all", limit=10)
        users = data.get("users", [])
    except ValueError as error:
        await callback.message.edit_text(
            f"❌ {error}",
            reply_markup=back_to_arena_keyboard(),
        )
        await callback.answer()
        return

    if not users:
        await callback.message.edit_text(
            "🏆 Hozircha reyting mavjud emas.",
            reply_markup=back_to_arena_keyboard(),
        )
        await callback.answer()
        return

    text = "🏆 <b>Match reytinglari</b>\n\n"

    for index, user in enumerate(users, start=1):
        text += (
            f"{index}. <code>{user['telegram_id']}</code>\n"
            f"⭐ Rating: <b>{user['rating']}</b>\n"
            f"✅ G‘alaba: {user['wins']} | ❌ Mag‘lubiyat: {user['losses']}\n"
            f"🔥 Streak: {user['win_streak']} | 🏆 Best: {user['best_win_streak']}\n\n"
        )

    await callback.message.edit_text(
        text,
        reply_markup=back_to_arena_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "arena_guide")
async def arena_guide(callback: CallbackQuery):
    try:
        guide = await get_match_guide()
    except ValueError as error:
        await callback.message.edit_text(
            f"❌ {error}",
            reply_markup=back_to_arena_keyboard(),
        )
        await callback.answer()
        return

    await callback.message.edit_text(
        f"📘 <b>{guide['title']}</b>\n\n{guide['text']}",
        reply_markup=back_to_arena_keyboard(),
    )
    await callback.answer()
