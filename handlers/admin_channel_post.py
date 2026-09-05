import asyncio
from html import escape

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from config import ADMIN_CHAT_ID, ADMIN_USER_IDS, MINIAPP_URL
from services.api import get_subscription_channels


router = Router()


class ChannelPostState(StatesGroup):
    selecting = State()
    waiting_content = State()
    confirming = State()
    sending = State()


def is_post_admin(user_id: int) -> bool:
    value = int(user_id)
    return value in ADMIN_USER_IDS or (bool(ADMIN_CHAT_ID) and value == ADMIN_CHAT_ID)


def post_channels_keyboard(
    channels: list[dict], selected_ids: set[int]
) -> InlineKeyboardMarkup:
    rows = []
    for channel in channels:
        channel_id = int(channel["id"])
        marker = "✅" if channel_id in selected_ids else "⬜"
        rows.append([InlineKeyboardButton(
            text=f"{marker} {channel['title']}",
            callback_data=f"postadmin:toggle:{channel_id}",
        )])
    rows.extend([
        [
            InlineKeyboardButton(text="✅ Hammasini tanlash", callback_data="postadmin:all"),
            InlineKeyboardButton(text="➡️ Davom etish", callback_data="postadmin:next"),
        ],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="postadmin:cancel")],
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def post_confirmation_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📤 Kanallarga yuborish", callback_data="postadmin:send")],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="postadmin:cancel")],
    ])


async def _load_channels(message: Message) -> list[dict] | None:
    try:
        channels = await get_subscription_channels()
    except Exception:
        await message.answer("❌ Kanallar ro‘yxatini olib bo‘lmadi. Qayta urinib ko‘ring.")
        return None
    if not channels:
        await message.answer("❌ Yuborish uchun kanal yo‘q. Avval /obuna_admin orqali kanal qo‘shing.")
        return None
    return channels


@router.message(Command("post_admin"))
async def channel_post_admin(message: Message, state: FSMContext) -> None:
    if not message.from_user or not is_post_admin(message.from_user.id):
        await message.answer("❌ Siz admin emassiz.")
        return
    channels = await _load_channels(message)
    if channels is None:
        return
    await state.set_state(ChannelPostState.selecting)
    await state.update_data(channels=channels, selected_ids=[])
    await message.answer(
        "📣 <b>Yangi kanal posti</b>\n\n"
        "Post yuboriladigan kanallarni tanlang:",
        reply_markup=post_channels_keyboard(channels, set()),
    )


async def _selection_data(state: FSMContext) -> tuple[list[dict], set[int]]:
    data = await state.get_data()
    channels = list(data.get("channels") or [])
    selected_ids = {int(value) for value in data.get("selected_ids") or []}
    return channels, selected_ids


@router.callback_query(ChannelPostState.selecting, F.data.startswith("postadmin:toggle:"))
async def channel_post_toggle(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_post_admin(callback.from_user.id):
        await callback.answer("Ruxsat yo‘q", show_alert=True)
        return
    channels, selected_ids = await _selection_data(state)
    try:
        channel_id = int((callback.data or "").rsplit(":", 1)[1])
    except ValueError:
        await callback.answer("Kanal noto‘g‘ri", show_alert=True)
        return
    available_ids = {int(channel["id"]) for channel in channels}
    if channel_id not in available_ids:
        await callback.answer("Kanal topilmadi", show_alert=True)
        return
    if channel_id in selected_ids:
        selected_ids.remove(channel_id)
    else:
        selected_ids.add(channel_id)
    await state.update_data(selected_ids=sorted(selected_ids))
    await callback.message.edit_reply_markup(
        reply_markup=post_channels_keyboard(channels, selected_ids)
    )
    await callback.answer(f"{len(selected_ids)} ta kanal tanlandi")


@router.callback_query(ChannelPostState.selecting, F.data == "postadmin:all")
async def channel_post_select_all(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_post_admin(callback.from_user.id):
        await callback.answer("Ruxsat yo‘q", show_alert=True)
        return
    channels, _selected_ids = await _selection_data(state)
    selected_ids = {int(channel["id"]) for channel in channels}
    await state.update_data(selected_ids=sorted(selected_ids))
    await callback.message.edit_reply_markup(
        reply_markup=post_channels_keyboard(channels, selected_ids)
    )
    await callback.answer("Barcha kanallar tanlandi")


@router.callback_query(ChannelPostState.selecting, F.data == "postadmin:next")
async def channel_post_content_step(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_post_admin(callback.from_user.id):
        await callback.answer("Ruxsat yo‘q", show_alert=True)
        return
    _channels, selected_ids = await _selection_data(state)
    if not selected_ids:
        await callback.answer("Kamida bitta kanalni tanlang", show_alert=True)
        return
    await state.set_state(ChannelPostState.waiting_content)
    await callback.message.edit_text(
        f"✅ {len(selected_ids)} ta kanal tanlandi.\n\n"
        "Endi postni yuboring:\n"
        "• rasm va uning ostidagi yozuv; yoki\n"
        "• oddiy matn.\n\n"
        "Bot yuborgan xabaringizning aynan o‘zini kanallarga nusxalaydi."
    )
    await callback.answer()


@router.message(ChannelPostState.waiting_content)
async def channel_post_preview(message: Message, state: FSMContext) -> None:
    if not message.from_user or not is_post_admin(message.from_user.id):
        await state.clear()
        return
    if not message.photo and not (message.text or "").strip():
        await message.answer("❌ Rasmga yozuv qo‘shib yoki oddiy matn ko‘rinishida yuboring.")
        return
    if message.photo and not (message.caption or "").strip():
        await message.answer("❌ Rasm ostiga post yozuvini ham qo‘shing.")
        return
    _channels, selected_ids = await _selection_data(state)
    await state.update_data(
        source_chat_id=message.chat.id,
        source_message_id=message.message_id,
    )
    await state.set_state(ChannelPostState.confirming)
    await message.answer(
        f"👆 <b>Post ko‘rinishi</b>\n\n"
        f"Post {len(selected_ids)} ta kanalga yuboriladi. Tasdiqlaysizmi?",
        reply_markup=post_confirmation_keyboard(),
    )


async def copy_post_to_channels(
    bot: Bot,
    *,
    source_chat_id: int,
    source_message_id: int,
    channels: list[dict],
) -> tuple[list[dict], list[dict]]:
    sent, failed = [], []
    for channel in channels:
        try:
            await bot.copy_message(
                chat_id=channel["chat_id"],
                from_chat_id=source_chat_id,
                message_id=source_message_id,
            )
            sent.append(channel)
        except Exception:
            failed.append(channel)
        await asyncio.sleep(0.05)
    return sent, failed


@router.callback_query(ChannelPostState.confirming, F.data == "postadmin:send")
async def channel_post_send(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    if not is_post_admin(callback.from_user.id):
        await callback.answer("Ruxsat yo‘q", show_alert=True)
        return
    data = await state.get_data()
    selected_ids = {int(value) for value in data.get("selected_ids") or []}
    source_chat_id = data.get("source_chat_id")
    source_message_id = data.get("source_message_id")
    if not source_chat_id or not source_message_id:
        await callback.answer("Post ma’lumoti topilmadi. Qaytadan boshlang.", show_alert=True)
        await state.clear()
        return
    try:
        current_channels = await get_subscription_channels()
    except Exception:
        await callback.answer("Kanallar ro‘yxatini yangilab bo‘lmadi", show_alert=True)
        return
    targets = [
        channel for channel in current_channels if int(channel["id"]) in selected_ids
    ]
    if not targets:
        await callback.answer("Tanlangan kanallar topilmadi", show_alert=True)
        await state.clear()
        return
    await state.set_state(ChannelPostState.sending)
    await callback.answer("Post yuborilmoqda...")
    await callback.message.edit_text("⏳ Post kanallarga yuborilmoqda...")
    sent, failed = await copy_post_to_channels(
        bot,
        source_chat_id=int(source_chat_id),
        source_message_id=int(source_message_id),
        channels=targets,
    )
    await state.clear()
    lines = [f"✅ {len(sent)} ta kanalga yuborildi."]
    if failed:
        names = ", ".join(escape(str(channel["title"])) for channel in failed)
        lines.append(f"❌ {len(failed)} ta kanalga yuborilmadi: {names}")
        lines.append("Botning kanaldagi post yuborish huquqini tekshiring.")
    await callback.message.edit_text("\n\n".join(lines))


@router.callback_query(F.data == "postadmin:cancel")
async def channel_post_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_post_admin(callback.from_user.id):
        await callback.answer("Ruxsat yo‘q", show_alert=True)
        return
    await state.clear()
    await callback.answer("Bekor qilindi")
    await callback.message.edit_text("❌ Post yuborish bekor qilindi.")


@router.message(Command("gamepost"))
async def publish_game_post(message: Message) -> None:
    """Keep the legacy one-channel LEVEL_GROUP post command available."""
    if not message.from_user or not is_post_admin(message.from_user.id):
        return
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) != 2 or not parts[1].strip():
        await message.answer("Foydalanish: <code>/gamepost @kanal_username</code>")
        return
    if not MINIAPP_URL:
        await message.answer("❌ MINIAPP_URL sozlanmagan.")
        return
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🎮 O‘ynash", url=MINIAPP_URL)
    ]])
    try:
        sent = await message.bot.send_message(
            chat_id=parts[1].strip(),
            text=(
                "🎮 <b>LEVEL_GROUP</b>\n\n"
                "eFootball Arena, Penalty Duel va boshqa imkoniyatlardan foydalaning.\n\n"
                "👇 O‘yinni boshlash uchun tugmani bosing."
            ),
            reply_markup=keyboard,
        )
    except Exception as error:
        await message.answer(
            "❌ Kanalga post yuborilmadi. Bot kanal admini ekanini tekshiring.\n"
            f"<code>{type(error).__name__}</code>"
        )
        return
    await message.answer(
        f"✅ Post kanalga yuborildi.\nMessage ID: <code>{sent.message_id}</code>"
    )
