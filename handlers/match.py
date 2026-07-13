from aiogram import F, Router
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    WebAppInfo,
)

from services.arena_links import ArenaMiniAppConfigError, build_arena_miniapp_url


router = Router()


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


async def _send_redirect(target, *, action="open", match_id=None, edit=False):
    text = (
        "🎮 <b>Arena amallari MiniApp’da bajariladi.</b>\n\n"
        "Match yaratish, qo‘shilish, tayyorlik, Room Code va evidence "
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


@router.message(F.text.in_(["🎮 1vs1 Arena", "1vs1 Arena", "/arena"]))
async def arena_menu_message(message: Message):
    await _send_redirect(message)


@router.callback_query(F.data.startswith("arena_"))
async def redirect_legacy_arena_callback(callback: CallbackQuery):
    action, match_id = _callback_target(callback.data or "arena_open")
    await _send_redirect(
        callback.message,
        action=action,
        match_id=match_id,
        edit=True,
    )
    await callback.answer()
