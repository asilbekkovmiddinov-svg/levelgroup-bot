import re

from aiogram import F, Router
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from config import ARENA_ADMIN_IDS


router = Router()
# Supports backend-style IDs ("DB #35", "Match #35") and the actual
# result-channel title format ("⚔️ ARENA — №35 MATCH").
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


@router.message(F.text.startswith("/arena_edit"))
async def add_old_result_edit_button(message: Message):
    """Attach the finished-result edit button to an old Arena channel post.

    Usage:
      - reply to the old Arena result post with /arena_edit; or
      - /arena_edit <match_id>
    """
    if not message.from_user or message.from_user.id not in ARENA_ADMIN_IDS:
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
        except Exception as error:
            await message.reply(
                f"⚠️ Eski xabarning tugmasini o‘zgartirib bo‘lmadi. Match #{match_id} uchun alohida tugma yuborildi."
            )

    await message.reply(
        f"🎮 Match #{match_id}\n\nEski natijani tahrirlash:",
        reply_markup=_edit_keyboard(match_id),
    )
