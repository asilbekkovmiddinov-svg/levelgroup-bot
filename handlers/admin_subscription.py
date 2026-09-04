from html import escape

from aiogram import Bot, F, Router
from aiogram.enums import ChatMemberStatus, ChatType
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from config import ADMIN_CHAT_ID, ADMIN_USER_IDS
from services.api import (
    create_subscription_channel,
    delete_subscription_channel,
    get_subscription_channels,
    update_subscription_channel,
)


router = Router()


class SubscriptionAdminState(StatesGroup):
    channel_payload = State()


def is_subscription_admin(user_id: int) -> bool:
    value = int(user_id)
    return value in ADMIN_USER_IDS or (bool(ADMIN_CHAT_ID) and value == ADMIN_CHAT_ID)


def admin_channels_keyboard(channels: list[dict]) -> InlineKeyboardMarkup:
    rows = []
    for channel in channels:
        channel_id = int(channel["id"])
        title = str(channel["title"])
        rows.append([
            InlineKeyboardButton(text=f"✏️ {title}", callback_data=f"subadmin:edit:{channel_id}"),
            InlineKeyboardButton(text="🗑", callback_data=f"subadmin:delete:{channel_id}"),
        ])
    rows.append([InlineKeyboardButton(text="➕ Kanal qo‘shish", callback_data="subadmin:add")])
    rows.append([InlineKeyboardButton(text="🔄 Yangilash", callback_data="subadmin:refresh")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def channels_text(channels: list[dict]) -> str:
    lines = [
        "🔐 <b>Majburiy obuna kanallari</b>",
        "",
        "Botdagi /start va MiniApp kirishi shu ro‘yxatni tekshiradi.",
        "",
    ]
    for index, channel in enumerate(channels, start=1):
        lines.extend([
            f"{index}. <b>{escape(str(channel['title']))}</b>",
            f"   ID: <code>{escape(str(channel['chat_id']))}</code>",
            f"   {escape(str(channel['url']))}",
        ])
    return "\n".join(lines)


async def show_subscription_admin(message: Message, *, edit: bool = False):
    try:
        channels = await get_subscription_channels()
        text = channels_text(channels)
        keyboard = admin_channels_keyboard(channels)
    except Exception:
        text = "❌ Kanallar ro‘yxatini olib bo‘lmadi. Backend sozlamalarini tekshiring."
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="🔄 Qayta urinish", callback_data="subadmin:refresh")
        ]])
    if edit:
        await message.edit_text(text, reply_markup=keyboard)
    else:
        await message.answer(text, reply_markup=keyboard)


@router.message(Command("obuna_admin"))
async def subscription_admin_command(message: Message, state: FSMContext):
    if not message.from_user or not is_subscription_admin(message.from_user.id):
        await message.answer("❌ Siz admin emassiz.")
        return
    await state.clear()
    await show_subscription_admin(message)


@router.callback_query(F.data == "subadmin:refresh")
async def subscription_admin_refresh(callback: CallbackQuery, state: FSMContext):
    if not is_subscription_admin(callback.from_user.id):
        await callback.answer("Ruxsat yo‘q", show_alert=True)
        return
    await state.clear()
    await callback.answer()
    await show_subscription_admin(callback.message, edit=True)


@router.callback_query(F.data == "subadmin:add")
async def subscription_admin_add(callback: CallbackQuery, state: FSMContext):
    if not is_subscription_admin(callback.from_user.id):
        await callback.answer("Ruxsat yo‘q", show_alert=True)
        return
    await state.set_state(SubscriptionAdminState.channel_payload)
    await state.update_data(mode="add")
    await callback.answer()
    await callback.message.answer(
        "Yangi kanalni 3 qator qilib yuboring:\n\n"
        "<code>@kanal_username\nKanal nomi\nhttps://t.me/kanal_username</code>\n\n"
        "Yopiq kanal uchun birinchi qatorga <code>-100...</code> ID, uchinchi "
        "qatorga taklif havolasini yozing. Bot kanalga admin qilingan bo‘lishi shart."
    )


@router.callback_query(F.data.startswith("subadmin:edit:"))
async def subscription_admin_edit(callback: CallbackQuery, state: FSMContext):
    if not is_subscription_admin(callback.from_user.id):
        await callback.answer("Ruxsat yo‘q", show_alert=True)
        return
    try:
        channel_id = int((callback.data or "").rsplit(":", 1)[1])
        channels = await get_subscription_channels()
        current = next(item for item in channels if int(item["id"]) == channel_id)
    except Exception:
        await callback.answer("Kanal topilmadi", show_alert=True)
        return
    await state.set_state(SubscriptionAdminState.channel_payload)
    await state.update_data(mode="edit", channel_id=channel_id, sort_order=current.get("sort_order", 0))
    await callback.answer()
    await callback.message.answer(
        "Kanalning yangi ma’lumotlarini 3 qator qilib yuboring:\n\n"
        f"<code>{escape(str(current['chat_id']))}\n"
        f"{escape(str(current['title']))}\n"
        f"{escape(str(current['url']))}</code>\n\n"
        "Bot yangi kanalga ham admin qilingan bo‘lishi shart."
    )


async def validate_channel_access(bot: Bot, chat_id: str) -> None:
    target: str | int = chat_id
    if chat_id.startswith("-"):
        target = int(chat_id)
    chat = await bot.get_chat(target)
    if chat.type not in {ChatType.CHANNEL, ChatType.SUPERGROUP}:
        raise ValueError("Faqat kanal yoki superguruh qo‘shish mumkin")
    member = await bot.get_chat_member(target, bot.id)
    if member.status not in {ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR}:
        raise ValueError("Avval botni kanalga admin qiling")


@router.message(SubscriptionAdminState.channel_payload)
async def subscription_admin_save(message: Message, state: FSMContext, bot: Bot):
    if not message.from_user or not is_subscription_admin(message.from_user.id):
        await state.clear()
        return
    parts = [part.strip() for part in (message.text or "").splitlines() if part.strip()]
    if len(parts) != 3:
        await message.answer("❌ Aynan 3 qator yuboring: kanal ID, nomi va Telegram havolasi.")
        return
    chat_id, title, url = parts
    if not (chat_id.startswith("@") or (chat_id.startswith("-") and chat_id[1:].isdigit())):
        await message.answer("❌ Kanal ID <code>@username</code> yoki <code>-100...</code> bo‘lishi kerak.")
        return
    if not (url.startswith("https://t.me/") or url.startswith("tg://")):
        await message.answer("❌ Telegram havolasini to‘g‘ri kiriting.")
        return
    try:
        await validate_channel_access(bot, chat_id)
    except Exception as error:
        await message.answer(f"❌ {escape(str(error) or 'Bot kanalni tekshira olmadi')}.")
        return
    data = await state.get_data()
    try:
        channels = await get_subscription_channels()
        payload = {
            "chat_id": chat_id,
            "title": title,
            "url": url,
            "sort_order": int(data.get("sort_order", len(channels))),
            "admin_id": message.from_user.id,
        }
        if data.get("mode") == "edit":
            await update_subscription_channel(int(data["channel_id"]), payload)
            success = "✅ Kanal almashtirildi."
        else:
            await create_subscription_channel(payload)
            success = "✅ Kanal majburiy obunaga qo‘shildi."
    except Exception as error:
        await message.answer(f"❌ {escape(str(error) or 'Kanalni saqlab bo‘lmadi')}")
        return
    await state.clear()
    await message.answer(success)
    await show_subscription_admin(message)


@router.callback_query(F.data.startswith("subadmin:delete:"))
async def subscription_admin_delete(callback: CallbackQuery, state: FSMContext):
    if not is_subscription_admin(callback.from_user.id):
        await callback.answer("Ruxsat yo‘q", show_alert=True)
        return
    try:
        channel_id = int((callback.data or "").rsplit(":", 1)[1])
        await delete_subscription_channel(channel_id)
    except Exception as error:
        await callback.answer(str(error) or "Kanalni o‘chirib bo‘lmadi", show_alert=True)
        return
    await state.clear()
    await callback.answer("Kanal o‘chirildi")
    await show_subscription_admin(callback.message, edit=True)
