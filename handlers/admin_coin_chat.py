from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from config import ADMIN_CHAT_ID
from services.api import coin_chat_action, get_active_coin_chats, get_coin_chat, mark_coin_chat_read, send_coin_chat_message

router = Router()

QUICK = {
    "REQUEST_CODE": "MyKonami emailingizga kod yuborildi. Iltimos, 6 xonali kodni shu yerga yozing.",
    "ACCEPT_CODE": "Kod qabul qilindi. Coin xaridi davom etmoqda.",
    "WRONG_CODE": "Kod noto‘g‘ri. Iltimos, kodni tekshirib qayta yuboring.",
    "RESEND_CODE": "Yangi kod yuborildi. Iltimos, yangi 6 xonali kodni yozing.",
}


class CoinChatState(StatesGroup):
    message = State()


def is_admin(user_id):
    return bool(ADMIN_CHAT_ID) and int(user_id) == int(ADMIN_CHAT_ID)


def keyboard(kind, order_id):
    prefix=f"coinchat:{kind}:{order_id}"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Kodni yuboring",callback_data=f"{prefix}:REQUEST_CODE"),
         InlineKeyboardButton(text="Kod qabul qilindi",callback_data=f"{prefix}:ACCEPT_CODE")],
        [InlineKeyboardButton(text="Kod noto‘g‘ri",callback_data=f"{prefix}:WRONG_CODE"),
         InlineKeyboardButton(text="Yangi kod yuboring",callback_data=f"{prefix}:RESEND_CODE")],
        [InlineKeyboardButton(text="Qabul qilish",callback_data=f"{prefix}:CLAIM"),
         InlineKeyboardButton(text="Coin topshirildi",callback_data=f"{prefix}:COMPLETE")],
        [InlineKeyboardButton(text="Xabar yozish",callback_data=f"{prefix}:WRITE"),
         InlineKeyboardButton(text="Rad etish",callback_data=f"{prefix}:REJECT")],
    ])


async def render(target, kind, order_id):
    result=await get_coin_chat(kind,order_id); messages=result.get("data",[])
    await mark_coin_chat_read(kind, order_id)
    transcript="\n\n".join(f"{'👤 User' if x.get('sender')=='USER' else '🛡 Operator'}:\n{x.get('message','')}" for x in messages[-10:]) or "Xabar yo‘q"
    await target.answer(f"💬 {kind} Coin Order #{order_id}\nStatus: {result.get('status','—')}\n\n{transcript}",reply_markup=keyboard(kind,order_id))


@router.message(Command("coin_chats"))
async def chats(message: Message):
    if not is_admin(message.from_user.id): return
    result=await get_active_coin_chats(); items=result.get("data",[])
    if not items: return await message.answer("Faol Coin chatlar yo‘q.")
    buttons=[[InlineKeyboardButton(text=f"💬 {x['order_type']} #{x['order_id']} · {x['status']} ({x.get('unread_count',0)})",callback_data=f"coinchatopen:{x['order_type']}:{x['order_id']}")] for x in items]
    await message.answer("Coin Order chatlari",reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@router.callback_query(F.data.startswith("coinchatopen:"))
async def open_chat(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return await callback.answer("Ruxsat yo‘q",show_alert=True)
    _,kind,raw_id=callback.data.split(":"); await render(callback.message,kind,int(raw_id)); await callback.answer()


@router.callback_query(F.data.startswith("coinchat:"))
async def quick(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): return await callback.answer("Ruxsat yo‘q",show_alert=True)
    _,kind,raw_id,action=callback.data.split(":"); order_id=int(raw_id)
    if action=="WRITE":
        await state.update_data(kind=kind,order_id=order_id); await state.set_state(CoinChatState.message)
        await callback.message.answer("Operator xabarini yozing:"); return await callback.answer()
    result=await coin_chat_action(kind,order_id,callback.from_user.id,action)
    if not result.get("success"): return await callback.answer(result.get("detail") or result.get("message") or "Xatolik",show_alert=True)
    if action in QUICK: await send_coin_chat_message(kind,order_id,callback.from_user.id,QUICK[action])
    await callback.answer("Yangilandi"); await render(callback.message,kind,order_id)


@router.message(CoinChatState.message)
async def operator_message(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    data=await state.get_data(); result=await send_coin_chat_message(data["kind"],data["order_id"],message.from_user.id,message.text or "")
    await state.clear(); await message.answer("Xabar yuborildi." if result.get("success") else "Xabar yuborilmadi.")
