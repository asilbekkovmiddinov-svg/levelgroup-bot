from aiogram import F, Router
from aiogram.filters import Filter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    WebAppInfo,
)

from services.arena_evidence_state import (
    ArenaEvidenceSession,
    DuplicateEvidenceError,
    evidence_store,
)
from services.arena_links import ArenaMiniAppConfigError, build_arena_miniapp_url
from services.arena_notifications import ArenaNotification, send_arena_notification
from services.match_api import ArenaApiError, upload_internal_evidence


router = Router()


class ArenaEvidenceState(StatesGroup):
    waiting_media = State()


class PendingArenaEvidence(Filter):
    async def __call__(self, message: Message) -> bool:
        return bool(message.from_user and evidence_store.get(message.from_user.id))


def arena_miniapp_keyboard(
    *, action: str = "open", match_id: int | None = None
) -> InlineKeyboardMarkup:
    url = build_arena_miniapp_url(action=action, match_id=match_id)
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🎮 Arena MiniApp’ni ochish",
                    web_app=WebAppInfo(url=url),
                )
            ]
        ]
    )


def _callback_target(data: str) -> tuple[str, int | None]:
    action = data.removeprefix("arena_").split(":", 1)[0] or "open"
    match_id = None
    if ":" in data:
        raw_match_id = data.rsplit(":", 1)[-1]
        if raw_match_id.isdigit():
            match_id = int(raw_match_id)
    return action, match_id


def _evidence_error(error: Exception) -> str:
    if isinstance(error, DuplicateEvidenceError):
        return "Bu evidence allaqachon qabul qilingan."
    if not isinstance(error, ArenaApiError):
        return "Evidence yuborishda xavfsiz ichki xatolik yuz berdi."
    if error.status == 409:
        return "Evidence avval yuborilgan yoki match holati o‘zgargan."
    if error.status in {401, 403}:
        return "Evidence yuborishga ruxsat berilmadi. Administratorga xabar bering."
    if error.status == 404:
        return "Arena match topilmadi."
    if error.status == 422:
        return "Evidence ma’lumoti noto‘g‘ri formatda."
    if error.status is not None and error.status >= 500:
        return "Arena serverida vaqtinchalik xatolik. Qayta urinib ko‘ring."
    return "Evidence qabul qilinmadi. Match holatini tekshiring."


def _progress_text(session: ArenaEvidenceSession, accepted: str | None = None) -> str:
    lines = []
    if accepted == "screenshot":
        lines.append("✅ <b>Screenshot qabul qilindi.</b>")
    elif accepted == "video":
        lines.append("✅ <b>Video qabul qilindi.</b>")
    if session.complete:
        lines.extend(("", "✅ <b>Evidence to‘liq qabul qilindi.</b>"))
    else:
        missing = "video" if session.screenshot_file_id else "screenshot"
        lines.extend(
            (
                "",
                "⏳ Yana bitta evidence qoldi.",
                f"Endi <b>{missing}</b> yuboring.",
            )
        )
    return "\n".join(lines)


async def _send_redirect(target, *, action="open", match_id=None, edit=False):
    text = (
        "🎮 <b>Arena amallari MiniApp’da bajariladi.</b>\n\n"
        "Match yaratish, qo‘shilish, tayyorlik va Room Code "
        "xavfsiz Telegram tasdiqlashi bilan MiniApp orqali yuboriladi."
    )
    try:
        markup = arena_miniapp_keyboard(action=action, match_id=match_id)
    except ArenaMiniAppConfigError:
        text = "❌ Arena MiniApp manzili hozircha sozlanmagan. Administratorga xabar bering."
        markup = None
    if edit:
        await target.edit_text(text, reply_markup=markup)
    else:
        await target.answer(text, reply_markup=markup)


async def _start_evidence(callback: CallbackQuery, state: FSMContext, match_id: int):
    session = evidence_store.start(callback.from_user.id, match_id)
    await state.set_state(ArenaEvidenceState.waiting_media)
    await state.update_data(match_id=match_id)
    await callback.message.edit_text(
        "📎 <b>Match evidence yuboring.</b>\n\n"
        "Screenshot va videoni istalgan tartibda, alohida xabar qilib yuboring.\n\n"
        + _progress_text(session)
    )
    await callback.answer()


async def _handle_evidence(message: Message, state: FSMContext):
    session = evidence_store.get(message.from_user.id)
    if not session:
        await state.clear()
        return
    if message.photo:
        media_type = "screenshot"
        file_id = message.photo[-1].file_id
        api_fields = {"screenshot_file_id": file_id}
    elif message.video:
        media_type = "video"
        file_id = message.video.file_id
        api_fields = {"video_file_id": file_id}
    else:
        await message.answer("❌ Screenshot rasm yoki video yuboring.")
        return
    if (
        media_type == "screenshot" and session.screenshot_file_id
    ) or (media_type == "video" and session.video_file_id):
        await message.answer("⚠️ Bu evidence turi allaqachon qabul qilingan.")
        return
    try:
        await upload_internal_evidence(
            match_id=session.match_id,
            telegram_id=message.from_user.id,
            **api_fields,
        )
        session = evidence_store.mark_accepted(
            message.from_user.id, media_type=media_type, file_id=file_id
        )
    except Exception as error:
        await message.answer(f"❌ {_evidence_error(error)}")
        return
    await message.answer(_progress_text(session, accepted=media_type))
    if session.complete:
        evidence_store.clear(message.from_user.id)
        await state.clear()
        await send_arena_notification(
            message.bot,
            message.from_user.id,
            ArenaNotification.ADMIN_REVIEW,
            match_id=session.match_id,
            detail="Evidence to‘liq qabul qilindi. Admin natijani tekshiradi.",
        )


@router.message(F.text.in_(["🎮 1vs1 Arena", "1vs1 Arena", "/arena"]))
async def arena_menu_message(message: Message):
    await _send_redirect(message)


@router.callback_query(F.data.startswith("arena_evidence:"))
async def arena_evidence_start(callback: CallbackQuery, state: FSMContext):
    raw_match_id = (callback.data or "").rsplit(":", 1)[-1]
    if not raw_match_id.isdigit():
        await callback.answer("Match ID noto‘g‘ri.", show_alert=True)
        return
    await _start_evidence(callback, state, int(raw_match_id))


@router.message(ArenaEvidenceState.waiting_media, F.photo | F.video)
async def arena_evidence_media(message: Message, state: FSMContext):
    await _handle_evidence(message, state)


@router.message(PendingArenaEvidence(), F.photo | F.video)
async def arena_evidence_recovery(message: Message, state: FSMContext):
    await state.set_state(ArenaEvidenceState.waiting_media)
    await _handle_evidence(message, state)


@router.message(ArenaEvidenceState.waiting_media)
async def arena_evidence_wrong_media(message: Message):
    await message.answer("❌ Screenshot rasm yoki video yuboring.")


@router.callback_query(F.data.startswith("arena_"))
async def redirect_legacy_arena_callback(callback: CallbackQuery):
    action, match_id = _callback_target(callback.data or "arena_open")
    await _send_redirect(callback.message, action=action, match_id=match_id, edit=True)
    await callback.answer()
