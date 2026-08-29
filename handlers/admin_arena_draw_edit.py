from aiogram import F, Router
from aiogram.types import CallbackQuery

from config import ARENA_ADMIN_IDS
from handlers.admin_arena_v4 import api_error_message, finished_result_edit_keyboard
from services.arena_v4_api import correct_finished_match_result


router = Router()


@router.callback_query(F.data.regexp(r"^arv4:e:confirm:(\d+):(\d+):\2$"))
async def confirm_finished_draw_edit(callback: CallbackQuery):
    """Allow an admin to correct a finished Arena V5 result to a draw.

    This router is registered before the legacy Arena V4 handler, whose correction
    callback still rejects equal scores for older penalty-only flows.
    """
    if callback.from_user.id not in ARENA_ADMIN_IDS:
        await callback.answer("Siz Arena admin emassiz.", show_alert=True)
        return

    parts = (callback.data or "").split(":")
    match_id = int(parts[3])
    score = int(parts[4])
    try:
        await correct_finished_match_result(match_id, callback.from_user.id, score, score)
        await callback.message.edit_reply_markup(reply_markup=finished_result_edit_keyboard(match_id))
        await callback.answer(
            f"✅ Match #{match_id} natijasi {score}:{score} ga tuzatildi.",
            show_alert=True,
        )
    except Exception as error:
        await callback.answer(api_error_message(error), show_alert=True)
