import re

from aiogram import F, Router
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from config import ARENA_ADMIN_IDS


router = Router()
_MATCH_ID_RE = re.compile(
    r"(?:DB\s*#|Match\s*#|ARENA\s*[—–-]?\s*(?:№|#)\s*)(\d+)",
    re.IGNORECASE,
)


def _edit_keyboard(match_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="✏️ Natijani tahrirlash",
            callback_data=f"arv4:e:start:{match_id}",
        )
    ]])


def _is_allowed_sender(message: Message, *, channel_post: bool = False) -> bool:
    if message.from_user and message.from_user.id in ARENA_ADMIN_IDS:
        return True
    # A real channel_post is authored by the channel itself. Telegram does not
    # expose the underlying admin user ID, so this path is only enabled for the
    # dedicated channel_post observer, never for ordinary user messages.
    return bool(channel_post and message.sender_chat and message.sender_chat.id == message.chat.id)


async def _handle_arena_edit(message: Message, *, channel_post: bool = False):
    if not _is_allowed_sender(message, channel_post=channel_post):
        await message.reply("❌ Siz Arena admin emassiz.")
        return

    parts = (message.text or "").split(maxsplit=1)
    match_id = None
    target = message.reply_to_message

    if len(parts) == 2 and parts[1].strip().isdigit():
        match_id = int(parts[1].strip())
    elif target:
        source = target.text or target.caption or ""
        found = _MATCH_ID_RE.search(source)
        if found:
            match_id = int(found.group(1))

    if not match_id:
        await message.reply(
            "Match raqamini xabardan aniqlab bo‘lmadi. "
            "Eski Arena natijasi xabariga reply qilib <code>/arena_edit</code> yuboring "
            "yoki <code>/arena_edit MATCH_ID</code> yozing."
        )
        return

    if target:
        try:
            await target.edit_reply_markup(reply_markup=_edit_keyboard(match_id))
            await message.reply(f"✅ Match #{match_id} uchun tahrirlash tugmasi qo‘shildi.")
            return
        except Exception:
            await message.reply(
                f"⚠️ Eski xabarning tugmasini o‘zgartirib bo‘lmadi. Match #{match_id} uchun alohida tugma yuborildi."
            )

    await message.reply(
        f"🎮 Match #{match_id}\n\nEski natijani tahrirlash:",
        reply_markup=_edit_keyboard(match_id),
    )


@router.message(F.text.startswith("/arena_edit"))
async def add_old_result_edit_button(message: Message):
    await _handle_arena_edit(message)


# Telegram delivers messages written *as a channel* through channel_post, not
# through the normal message observer. Without this observer the command is
# invisible to @router.message regardless of sender_chat checks.
@router.channel_post(F.text.startswith("/arena_edit"))
async def add_old_result_edit_button_channel_post(message: Message):
    await _handle_arena_edit(message, channel_post=True)
