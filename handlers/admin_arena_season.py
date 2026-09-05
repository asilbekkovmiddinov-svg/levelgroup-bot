from datetime import datetime
from html import escape

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from config import ADMIN_CHAT_ID, ADMIN_USER_IDS, ARENA_ADMIN_IDS
from services.arena_v5_api import (
    ArenaApiError,
    create_season,
    finish_season,
    list_seasons,
    update_season_duration,
)


router = Router()


class ArenaSeasonAdminState(StatesGroup):
    name = State()
    duration = State()
    prize = State()
    edit_duration = State()


def is_arena_season_admin(user_id: int) -> bool:
    value = int(user_id)
    return (
        value in ARENA_ADMIN_IDS
        or value in ADMIN_USER_IDS
        or (bool(ADMIN_CHAT_ID) and value == ADMIN_CHAT_ID)
    )


def _date(value: str | None) -> str:
    if not value:
        return "—"
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).strftime(
            "%d.%m.%Y %H:%M UTC"
        )
    except (TypeError, ValueError):
        return str(value)


def seasons_text(seasons: list[dict]) -> str:
    lines = [
        "🏟 <b>Arena mavsumlari</b>",
        "",
        "Har bir mavsum: g‘alaba +3, durang +1, mag‘lubiyat +0, yangi referal +3.",
        "",
    ]
    if not seasons:
        lines.append("Hali Arena mavsumi ochilmagan.")
    for season in seasons:
        icon = "🟢" if season["status"] == "ACTIVE" else "✅"
        lines.extend([
            f"{icon} <b>#{season['id']} {escape(str(season['name']))}</b>",
            f"   Holat: {season['status']} • {season['duration_days']} kun",
            f"   {_date(season.get('starts_at'))} — {_date(season.get('ends_at'))}",
            f"   Match: {season.get('match_count', 0)} • Referal: {season.get('referral_count', 0)}",
        ])
    return "\n".join(lines)


def seasons_keyboard(seasons: list[dict]) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text="➕ Yangi mavsum ochish", callback_data="arseason:create")]]
    active = next((item for item in seasons if item["status"] == "ACTIVE"), None)
    if active:
        rows.append([InlineKeyboardButton(
            text=f"⏱ #{active['id']} muddatini o‘zgartirish",
            callback_data=f"arseason:duration:{active['id']}",
        )])
        rows.append([InlineKeyboardButton(
            text=f"⏹ #{active['id']} mavsumni yakunlash",
            callback_data=f"arseason:finish:{active['id']}",
        )])
    rows.append([InlineKeyboardButton(text="🔄 Yangilash", callback_data="arseason:refresh")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def show_arena_seasons(message: Message, *, edit: bool = False) -> None:
    try:
        payload = await list_seasons()
        seasons = payload.get("seasons") or []
        text = seasons_text(seasons)
        keyboard = seasons_keyboard(seasons)
    except Exception:
        text = "❌ Arena mavsumlarini olib bo‘lmadi. Backend sozlamalarini tekshiring."
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="🔄 Qayta urinish", callback_data="arseason:refresh")
        ]])
    if edit:
        await message.edit_text(text, reply_markup=keyboard)
    else:
        await message.answer(text, reply_markup=keyboard)


@router.message(Command("arena_admin"))
async def arena_season_admin(message: Message, state: FSMContext) -> None:
    if not message.from_user or not is_arena_season_admin(message.from_user.id):
        await message.answer("❌ Siz Arena admin emassiz.")
        return
    await state.clear()
    await show_arena_seasons(message)


@router.callback_query(F.data == "arseason:refresh")
async def arena_season_refresh(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_arena_season_admin(callback.from_user.id):
        await callback.answer("Ruxsat yo‘q", show_alert=True)
        return
    await state.clear()
    await callback.answer()
    await show_arena_seasons(callback.message, edit=True)


@router.callback_query(F.data == "arseason:create")
async def arena_season_create_start(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_arena_season_admin(callback.from_user.id):
        await callback.answer("Ruxsat yo‘q", show_alert=True)
        return
    await state.clear()
    await state.set_state(ArenaSeasonAdminState.name)
    await callback.answer()
    await callback.message.answer("Yangi Arena mavsumi nomini yuboring. Masalan: <b>Haftalik Arena</b>")


@router.message(ArenaSeasonAdminState.name)
async def arena_season_name(message: Message, state: FSMContext) -> None:
    if not message.from_user or not is_arena_season_admin(message.from_user.id):
        await state.clear()
        return
    name = " ".join((message.text or "").strip().split())
    if not 1 <= len(name) <= 80:
        await message.answer("❌ Mavsum nomi 1–80 ta belgi bo‘lsin.")
        return
    await state.update_data(name=name)
    await state.set_state(ArenaSeasonAdminState.duration)
    await message.answer("Arena necha kun davom etadi? <b>1 dan 365 gacha</b> son yuboring.")


@router.message(ArenaSeasonAdminState.duration)
async def arena_season_duration(message: Message, state: FSMContext) -> None:
    if not message.from_user or not is_arena_season_admin(message.from_user.id):
        await state.clear()
        return
    try:
        duration_days = int((message.text or "").strip())
    except ValueError:
        duration_days = 0
    if not 1 <= duration_days <= 365:
        await message.answer("❌ 1 dan 365 gacha kun sonini yuboring.")
        return
    await state.update_data(duration_days=duration_days)
    await state.set_state(ArenaSeasonAdminState.prize)
    await message.answer("Mavsum sovrini matnini yuboring. Sovrin bo‘lmasa <code>-</code> yuboring.")


@router.callback_query(F.data.startswith("arseason:duration:"))
async def arena_season_duration_start(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_arena_season_admin(callback.from_user.id):
        await callback.answer("Ruxsat yo‘q", show_alert=True)
        return
    season_id = int((callback.data or "").rsplit(":", 1)[1])
    await state.clear()
    await state.update_data(season_id=season_id)
    await state.set_state(ArenaSeasonAdminState.edit_duration)
    await callback.answer()
    await callback.message.answer(
        f"Faol Arena <b>#{season_id}</b> uchun yangi umumiy davomiylikni yuboring (1–365 kun)."
    )


@router.message(ArenaSeasonAdminState.edit_duration)
async def arena_season_duration_save(message: Message, state: FSMContext) -> None:
    if not message.from_user or not is_arena_season_admin(message.from_user.id):
        await state.clear()
        return
    try:
        duration_days = int((message.text or "").strip())
    except ValueError:
        duration_days = 0
    if not 1 <= duration_days <= 365:
        await message.answer("❌ 1 dan 365 gacha kun sonini yuboring.")
        return
    data = await state.get_data()
    try:
        season = await update_season_duration(
            int(data["season_id"]),
            admin_id=message.from_user.id,
            duration_days=duration_days,
        )
    except ArenaApiError as error:
        await message.answer(f"❌ {escape(str(error))}")
        return
    except Exception:
        await message.answer("❌ Arena muddatini o‘zgartirib bo‘lmadi.")
        return
    await state.clear()
    await message.answer(
        f"✅ <b>{escape(str(season['name']))}</b> muddati {duration_days} kunga o‘zgardi.\n"
        f"Yangi tugash vaqti: {_date(season.get('ends_at'))}"
    )
    await show_arena_seasons(message)


@router.message(ArenaSeasonAdminState.prize)
async def arena_season_prize(message: Message, state: FSMContext) -> None:
    if not message.from_user or not is_arena_season_admin(message.from_user.id):
        await state.clear()
        return
    prize = (message.text or "").strip()
    if len(prize) > 500:
        await message.answer("❌ Sovrin matni 500 ta belgidan oshmasin.")
        return
    data = await state.get_data()
    try:
        season = await create_season(
            admin_id=message.from_user.id,
            name=data["name"],
            duration_days=int(data["duration_days"]),
            prize_text=None if prize == "-" else prize,
        )
    except ArenaApiError as error:
        await message.answer(f"❌ {escape(str(error))}")
        return
    except Exception:
        await message.answer("❌ Arena mavsumini ochib bo‘lmadi. Qayta urinib ko‘ring.")
        return
    await state.clear()
    await message.answer(
        f"✅ <b>{escape(str(season['name']))}</b> ochildi.\n"
        f"Davomiyligi: {season['duration_days']} kun\n"
        f"Tugaydi: {_date(season.get('ends_at'))}"
    )
    await show_arena_seasons(message)


@router.callback_query(F.data.startswith("arseason:finish:"))
async def arena_season_finish_confirm(callback: CallbackQuery) -> None:
    if not is_arena_season_admin(callback.from_user.id):
        await callback.answer("Ruxsat yo‘q", show_alert=True)
        return
    season_id = int((callback.data or "").rsplit(":", 1)[1])
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Ha, yakunlash", callback_data=f"arseason:finish-ok:{season_id}")],
        [InlineKeyboardButton(text="↩️ Bekor qilish", callback_data="arseason:refresh")],
    ])
    await callback.answer()
    await callback.message.answer(
        f"⚠️ Arena mavsumi <b>#{season_id}</b> hozir yakunlansinmi? Reyting arxivda saqlanadi.",
        reply_markup=keyboard,
    )


@router.callback_query(F.data.startswith("arseason:finish-ok:"))
async def arena_season_finish(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_arena_season_admin(callback.from_user.id):
        await callback.answer("Ruxsat yo‘q", show_alert=True)
        return
    season_id = int((callback.data or "").rsplit(":", 1)[1])
    try:
        await finish_season(season_id, admin_id=callback.from_user.id)
    except ArenaApiError as error:
        await callback.answer(str(error), show_alert=True)
        return
    except Exception:
        await callback.answer("Mavsumni yakunlab bo‘lmadi", show_alert=True)
        return
    await state.clear()
    await callback.answer("Mavsum yakunlandi")
    await callback.message.answer("✅ Arena mavsumi yakunlandi. Reyting arxivda saqlandi.")
    await show_arena_seasons(callback.message)
