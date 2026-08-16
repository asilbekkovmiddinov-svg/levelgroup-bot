import asyncio
from datetime import datetime
from html import escape

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.base import StorageKey
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from config import ARENA_ADMIN_IDS
from services.arena_v4_api import (
    ArenaApiError,
    cancel_match,
    claim_match_review,
    claim_review,
    get_review_detail,
    list_reviews,
    submit_appeal_decision,
    submit_score,
    submit_match_score,
    cancel_channel_match,
)


router = Router()
_in_flight: set[int] = set()
_guard = asyncio.Lock()


class ArenaV4AdminState(StatesGroup):
    normal_player_a_score = State()
    normal_player_b_score = State()
    appeal_player_a_score = State()
    appeal_player_b_score = State()


def is_arena_admin(user_id: int) -> bool:
    return user_id in ARENA_ADMIN_IDS


def _private_admin_state(
    state: FSMContext, *, bot_id: int, admin_id: int
) -> FSMContext:
    return FSMContext(
        storage=state.storage,
        key=StorageKey(
            bot_id=bot_id,
            chat_id=admin_id,
            user_id=admin_id,
        ),
    )


async def _start_private_input(
    callback: CallbackQuery,
    state: FSMContext,
    *,
    data: dict,
    next_state: State,
    prompt: str,
) -> bool:
    await state.clear()
    private_state = _private_admin_state(
        state,
        bot_id=callback.bot.id,
        admin_id=callback.from_user.id,
    )
    await private_state.clear()
    await private_state.update_data(**data)
    await private_state.set_state(next_state)
    try:
        await callback.bot.send_message(callback.from_user.id, prompt)
    except Exception:
        await private_state.clear()
        await callback.answer(
            "Avval Bot shaxsiy chatida /start bosing.",
            show_alert=True,
        )
        return False
    await callback.answer(
        "Hisobni Bot shaxsiy chatida kiriting.",
        show_alert=True,
    )
    return True


def _safe(value) -> str:
    return escape(str(value if value is not None else "—"), quote=True)


def _time(value) -> str:
    if not value:
        return "—"
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).strftime(
            "%d.%m.%Y %H:%M UTC"
        )
    except (TypeError, ValueError):
        return str(value)


def _profile(label: str, profile: dict, efootball_name: str | None) -> str:
    username = (
        f"@{profile['username']}" if profile.get("username") else "username yo‘q"
    )
    return (
        f"<b>{label}</b>\n"
        f"Telegram: {_safe(profile.get('display_name'))}\n"
        f"Username: {_safe(username)}\n"
        f"Telegram ID: <code>{_safe(profile.get('telegram_id'))}</code>\n"
        f"eFootball: <b>{_safe(efootball_name)}</b>"
    )


def format_review(detail: dict) -> str:
    review, match = detail["review"], detail["match"]
    screenshots = detail.get("screenshots") or []
    uploaded = ", ".join(_time(item.get("uploaded_at")) for item in screenshots)
    text = (
        "🎮 <b>Arena V4 Admin Review</b>\n\n"
        f"Review: <code>#{_safe(review['id'])}</code>\n"
        f"Match: <code>{_safe(match['public_id'])}</code> "
        f"(DB #{_safe(match['id'])})\n\n"
        f"{_profile('Player A', detail['player_a'], match.get('owner_efootball_username'))}\n\n"
        f"{_profile('Player B', detail['player_b'], match.get('opponent_efootball_username'))}\n\n"
        f"Stake: <b>{_safe(match['stake_efc'])} EFC</b>\n"
        f"Total pot: <b>{_safe(match['total_pool_efc'])} EFC</b>\n"
        f"Platform fee: <b>{_safe(match['commission_efc'])} EFC</b>\n"
        f"Winner reward: <b>{_safe(match['winner_reward_efc'])} EFC</b>\n"
        f"Match yaratildi: {_safe(_time(match.get('created_at')))}\n"
        f"Screenshot yuborildi: {_safe(uploaded or '—')}"
    )
    appeal = detail.get("appeal")
    if appeal:
        text += (
            "\n\n⚠️ <b>APPEAL</b>\n"
            f"Sabab: {_safe(appeal.get('reason'))}\n"
            f"Eski score: <b>{_safe(match.get('owner_score'))} : "
            f"{_safe(match.get('opponent_score'))}</b>\n"
            f"Eski winner: <code>{_safe(match.get('winner_id') or 'Draw')}</code>"
        )
    return text


def review_keyboard(review_id: int, review_type: str) -> InlineKeyboardMarkup:
    if review_type == "APPEAL":
        actions = [
            ("✅ Qarorni qoldirish", f"arv4:appeal:keep:{review_id}"),
            ("✏️ Hisobni yangilash", f"arv4:appeal:score:{review_id}"),
            ("❌ Matchni bekor qilish", f"arv4:appeal:cancel:{review_id}"),
        ]
    else:
        actions = [
            ("📝 Hisobni kiritish", f"arv4:score:{review_id}"),
            ("❌ Matchni bekor qilish", f"arv4:cancel:{review_id}"),
        ]
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=text, callback_data=data)]
            for text, data in actions
        ]
    )


def queue_keyboard(reviews: list[dict]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text=f"Ko‘rish — Review #{item['id']}",
                callback_data=f"arv4:open:{item['id']}",
            )]
            for item in reviews
        ]
    )


def api_error_message(error: Exception) -> str:
    if not isinstance(error, ArenaApiError):
        return "Arena V4 ichki xatoligi."
    if error.status == 409:
        return (
            "Match hali admin tekshiruviga tayyor emas, boshqa admin "
            "tomonidan olingan yoki yakunlangan."
        )
    if error.status in {401, 403}:
        return "Backend Internal API autentifikatsiyasi noto‘g‘ri."
    if error.status == 404:
        return "Review topilmadi."
    return "Backend bilan aloqa xatoligi. Qayta urinib ko‘ring."


async def _show_queue(message: Message, review_type: str):
    if not is_arena_admin(message.from_user.id):
        await message.answer("❌ Siz Arena admin emassiz.")
        return
    try:
        data = await list_reviews(review_type)
    except Exception as error:
        await message.answer(api_error_message(error))
        return
    reviews = data.get("reviews") or []
    title = "Appeal queue" if review_type == "APPEAL" else "Normal review queue"
    if not reviews:
        await message.answer(f"✅ {title} bo‘sh.")
        return
    await message.answer(
        f"📋 <b>{title}</b>\n\nKutilayotgan reviewlar: {len(reviews)}",
        reply_markup=queue_keyboard(reviews),
    )


@router.message(F.text == "/arena_reviews")
async def normal_review_queue(message: Message):
    await _show_queue(message, "INITIAL")


@router.message(F.text == "/arena_appeals")
async def appeal_review_queue(message: Message):
    await _show_queue(message, "APPEAL")


async def _send_media(callback: CallbackQuery, detail: dict):
    for item in detail.get("screenshots") or []:
        url = item.get("media_url")
        if url:
            label = "A" if item["player_id"] == detail["match"]["owner_id"] else "B"
            await callback.bot.send_photo(
                callback.from_user.id, url, caption=f"📸 Player {label} screenshot"
            )
    appeal = detail.get("appeal")
    if appeal and appeal.get("video_url"):
        await callback.bot.send_video(
            callback.from_user.id,
            appeal["video_url"],
            caption="🎥 Appeal video",
        )


@router.callback_query(F.data.startswith("arv4:open:"))
async def open_review(callback: CallbackQuery):
    if not is_arena_admin(callback.from_user.id):
        await callback.answer("Siz Arena admin emassiz.", show_alert=True)
        return
    try:
        review_id = int((callback.data or "").rsplit(":", 1)[1])
        await claim_review(review_id, callback.from_user.id)
        detail = await get_review_detail(review_id)
        await _send_media(callback, detail)
        await callback.message.answer(
            format_review(detail),
            reply_markup=review_keyboard(
                review_id, detail["review"]["review_type"]
            ),
        )
        await callback.answer("Review sizga biriktirildi.")
    except Exception as error:
        await callback.answer(api_error_message(error), show_alert=True)


async def _start_score(
    callback: CallbackQuery, state: FSMContext, *, appeal: bool
):
    if not is_arena_admin(callback.from_user.id):
        await callback.answer("Siz Arena admin emassiz.", show_alert=True)
        return
    review_id = int((callback.data or "").rsplit(":", 1)[1])
    await _start_private_input(
        callback,
        state,
        data={"review_id": review_id, "appeal": appeal},
        next_state=(
            ArenaV4AdminState.appeal_player_a_score
            if appeal else ArenaV4AdminState.normal_player_a_score
        ),
        prompt="Player A hisobini kiriting (0–99):",
    )


@router.callback_query(F.data.startswith("arv4:score:"))
async def start_normal_score(callback: CallbackQuery, state: FSMContext):
    await _start_score(callback, state, appeal=False)


def channel_score_keyboard(
    match_id: int, owner_score: int = 0, opponent_score: int = 0
) -> InlineKeyboardMarkup:
    def adjust(action: str) -> str:
        return (
            f"arv4:m:adj:{match_id}:{owner_score}:{opponent_score}:{action}"
        )

    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="A ➖", callback_data=adjust("a-")),
            InlineKeyboardButton(
                text=f"⚽ A {owner_score}:{opponent_score} B",
                callback_data=f"arv4:m:noop:{match_id}",
            ),
            InlineKeyboardButton(text="A ➕", callback_data=adjust("a+")),
        ],
        [
            InlineKeyboardButton(text="B ➖", callback_data=adjust("b-")),
            InlineKeyboardButton(
                text="♻️ 0:0",
                callback_data=f"arv4:m:reset:{match_id}",
            ),
            InlineKeyboardButton(text="B ➕", callback_data=adjust("b+")),
        ],
        [InlineKeyboardButton(
            text="✅ Natijani tasdiqlash",
            callback_data=(
                f"arv4:m:confirm:{match_id}:{owner_score}:{opponent_score}"
            ),
        )],
        [InlineKeyboardButton(
            text="❌ Matchni bekor qilish",
            callback_data=(
                f"arv4:m:cancel:{match_id}:{owner_score}:{opponent_score}"
            ),
        )],
    ])


def channel_cancel_keyboard(
    match_id: int, owner_score: int = 0, opponent_score: int = 0
) -> InlineKeyboardMarkup:
    reasons = [
        ("Soxta screenshot", "F"),
        ("Match o‘ynalmagan", "N"),
        ("Qoida buzilgan", "R"),
        ("Texnik muammo", "T"),
    ]
    rows = [[InlineKeyboardButton(
        text=text, callback_data=f"arv4:m:cx:{match_id}:{code}"
    )] for text, code in reasons]
    rows.append([InlineKeyboardButton(
        text="↩️ Hisobga qaytish",
        callback_data=(
            f"arv4:m:back:{match_id}:{owner_score}:{opponent_score}"
        ),
    )])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _channel_score_parts(data: str, action: str) -> tuple[int, int, int]:
    prefix = f"arv4:m:{action}:"
    match_id, owner_score, opponent_score = data.removeprefix(prefix).split(":")
    return int(match_id), int(owner_score), int(opponent_score)


async def _claim_channel(callback: CallbackQuery, match_id: int) -> bool:
    if not is_arena_admin(callback.from_user.id):
        await callback.answer("Siz Arena admin emassiz.", show_alert=True)
        return False
    try:
        await claim_match_review(match_id, callback.from_user.id)
        return True
    except Exception as error:
        await callback.answer(api_error_message(error), show_alert=True)
        return False


@router.callback_query(F.data.startswith("arv4:m:start:"))
@router.callback_query(F.data.startswith("arv4:match:score:"))
async def start_channel_score(callback: CallbackQuery):
    match_id = int((callback.data or "").rsplit(":", 1)[1])
    if not await _claim_channel(callback, match_id):
        return
    await callback.message.edit_reply_markup(
        reply_markup=channel_score_keyboard(match_id)
    )
    await callback.answer(f"Match #{match_id} sizga biriktirildi.")


@router.callback_query(F.data.startswith("arv4:m:adj:"))
async def adjust_channel_score(callback: CallbackQuery):
    parts = (callback.data or "").split(":")
    match_id, owner_score, opponent_score = map(int, parts[3:6])
    action = parts[6]
    if not await _claim_channel(callback, match_id):
        return
    if action == "a-":
        owner_score = max(0, owner_score - 1)
    elif action == "a+":
        owner_score = min(99, owner_score + 1)
    elif action == "b-":
        opponent_score = max(0, opponent_score - 1)
    elif action == "b+":
        opponent_score = min(99, opponent_score + 1)
    await callback.message.edit_reply_markup(
        reply_markup=channel_score_keyboard(
            match_id, owner_score, opponent_score
        )
    )
    await callback.answer()


@router.callback_query(F.data.startswith("arv4:m:reset:"))
async def reset_channel_score(callback: CallbackQuery):
    match_id = int((callback.data or "").rsplit(":", 1)[1])
    if not await _claim_channel(callback, match_id):
        return
    await callback.message.edit_reply_markup(
        reply_markup=channel_score_keyboard(match_id)
    )
    await callback.answer("Hisob 0:0 qilindi.")


@router.callback_query(F.data.startswith("arv4:m:noop:"))
async def channel_score_noop(callback: CallbackQuery):
    await callback.answer("Hisob A : B ko‘rinishida.")


@router.callback_query(F.data.startswith("arv4:m:confirm:"))
async def confirm_channel_score(callback: CallbackQuery):
    match_id, owner_score, opponent_score = _channel_score_parts(
        callback.data or "", "confirm"
    )
    if not is_arena_admin(callback.from_user.id):
        await callback.answer("Siz Arena admin emassiz.", show_alert=True)
        return
    if owner_score == opponent_score:
        await callback.answer(
            "Teng hisob qabul qilinmaydi. Penalty natijasini kiriting.",
            show_alert=True,
        )
        return

    async def action():
        return await submit_match_score(
            match_id, callback.from_user.id, owner_score, opponent_score
        )

    try:
        applied = await _exclusive_action(match_id, action)
        if not applied:
            await callback.answer(
                "Bu match natijasi hozir saqlanmoqda.", show_alert=True
            )
            return
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
        await callback.answer(
            f"✅ Match #{match_id}: {owner_score}:{opponent_score} saqlandi.",
            show_alert=True,
        )
    except Exception as error:
        await callback.answer(api_error_message(error), show_alert=True)


@router.callback_query(F.data.startswith("arv4:appeal:score:"))
async def start_appeal_score(callback: CallbackQuery, state: FSMContext):
    await _start_score(callback, state, appeal=True)


def _parse_score(message: Message) -> int | None:
    text = (message.text or "").strip()
    if not text.isdigit():
        return None
    score = int(text)
    return score if 0 <= score <= 99 else None


@router.message(ArenaV4AdminState.normal_player_a_score)
@router.message(ArenaV4AdminState.appeal_player_a_score)
async def player_a_score(message: Message, state: FSMContext):
    score = _parse_score(message)
    if score is None:
        await message.answer("0 dan 99 gacha butun son kiriting.")
        return
    data = await state.get_data()
    await state.update_data(owner_score=score)
    await state.set_state(
        ArenaV4AdminState.appeal_player_b_score
        if data.get("appeal") else ArenaV4AdminState.normal_player_b_score
    )
    await message.answer("Player B hisobini kiriting (0–99):")


@router.message(ArenaV4AdminState.normal_player_b_score)
@router.message(ArenaV4AdminState.appeal_player_b_score)
async def player_b_score(message: Message, state: FSMContext):
    if not is_arena_admin(message.from_user.id):
        await state.clear()
        return
    opponent_score = _parse_score(message)
    if opponent_score is None:
        await message.answer("0 dan 99 gacha butun son kiriting.")
        return
    data = await state.get_data()
    try:
        if data.get("appeal"):
            result = await submit_appeal_decision(
                data["review_id"],
                message.from_user.id,
                "UPDATE_SCORE",
                owner_score=data["owner_score"],
                opponent_score=opponent_score,
            )
        else:
            if data["owner_score"] == opponent_score:
                await message.answer("Teng hisob qabul qilinmaydi. Penalty natijasini kiriting.")
                return
            if data.get("match_id"):
                result = await submit_match_score(
                    data["match_id"], message.from_user.id,
                    data["owner_score"], opponent_score,
                )
            else:
                result = await submit_score(
                    data["review_id"], message.from_user.id,
                    data["owner_score"], opponent_score,
                )
    except Exception as error:
        await message.answer(api_error_message(error))
        return
    await state.clear()
    await message.answer(
        "✅ Hisob backendga saqlandi.\n"
        f"Natija: <b>{_safe(result.get('decision'))}</b>"
    )


async def _exclusive_action(review_id: int, action):
    async with _guard:
        if review_id in _in_flight:
            return False
        _in_flight.add(review_id)
    try:
        await action()
        return True
    finally:
        async with _guard:
            _in_flight.discard(review_id)


async def _direct_action(callback: CallbackQuery, action_name: str):
    if not is_arena_admin(callback.from_user.id):
        await callback.answer("Siz Arena admin emassiz.", show_alert=True)
        return
    review_id = int((callback.data or "").rsplit(":", 1)[1])

    async def action():
        if action_name == "CANCEL":
            return await cancel_match(review_id, callback.from_user.id)
        return await submit_appeal_decision(
            review_id, callback.from_user.id, action_name
        )

    try:
        applied = await _exclusive_action(review_id, action)
        if not applied:
            await callback.answer(
                "Bu review hozir bajarilmoqda.", show_alert=True
            )
            return
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.answer("Qaror backendga saqlandi.")
    except Exception as error:
        await callback.answer(api_error_message(error), show_alert=True)


@router.callback_query(F.data.startswith("arv4:cancel:"))
async def normal_cancel(callback: CallbackQuery):
    await _direct_action(callback, "CANCEL")


@router.callback_query(F.data.startswith("arv4:m:cancel:"))
@router.callback_query(F.data.startswith("arv4:match:cancel:"))
async def start_channel_cancel(callback: CallbackQuery):
    parts = (callback.data or "").split(":")
    match_id = int(parts[3])
    owner_score = int(parts[4]) if len(parts) > 4 else 0
    opponent_score = int(parts[5]) if len(parts) > 5 else 0
    if not await _claim_channel(callback, match_id):
        return
    await callback.message.edit_reply_markup(
        reply_markup=channel_cancel_keyboard(
            match_id, owner_score, opponent_score
        )
    )
    await callback.answer("Bekor qilish sababini tanlang.")


@router.callback_query(F.data.startswith("arv4:m:back:"))
async def back_to_channel_score(callback: CallbackQuery):
    match_id, owner_score, opponent_score = _channel_score_parts(
        callback.data or "", "back"
    )
    if not await _claim_channel(callback, match_id):
        return
    await callback.message.edit_reply_markup(
        reply_markup=channel_score_keyboard(
            match_id, owner_score, opponent_score
        )
    )
    await callback.answer()


@router.callback_query(F.data.startswith("arv4:m:cx:"))
async def submit_channel_cancel_reason(callback: CallbackQuery):
    parts = (callback.data or "").split(":")
    match_id = int(parts[3])
    reason = {
        "F": "FAKE_SCREENSHOT",
        "N": "MATCH_NOT_PLAYED",
        "R": "RULE_VIOLATION",
        "T": "TECHNICAL_ISSUE",
    }.get(parts[4])
    if not is_arena_admin(callback.from_user.id):
        await callback.answer("Siz Arena admin emassiz.", show_alert=True)
        return
    if reason is None:
        await callback.answer("Noto‘g‘ri sabab kodi.", show_alert=True)
        return

    async def action():
        return await cancel_channel_match(
            match_id, callback.from_user.id, reason
        )

    try:
        applied = await _exclusive_action(match_id, action)
        if not applied:
            await callback.answer(
                "Bu match qarori hozir saqlanmoqda.", show_alert=True
            )
            return
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
        await callback.answer(
            f"✅ Match #{match_id} bekor qilindi.", show_alert=True
        )
    except Exception as error:
        await callback.answer(api_error_message(error), show_alert=True)


@router.callback_query(F.data.startswith("arv4:appeal:keep:"))
async def appeal_keep(callback: CallbackQuery):
    await _direct_action(callback, "KEEP_RESULT")


@router.callback_query(F.data.startswith("arv4:appeal:cancel:"))
async def appeal_cancel(callback: CallbackQuery):
    await _direct_action(callback, "CANCEL_MATCH")
