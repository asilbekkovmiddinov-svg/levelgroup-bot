from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message, WebAppInfo

from config import ADMIN_CHAT_ID
from services.api import coin_chat_action, get_active_coin_chats, get_coin_chat, mark_coin_chat_read, open_coin_credentials, send_coin_chat_message

router = Router()

QUICK = {
    "OTP_SENT": "Email manzilingizga tasdiqlash kodi yuborildi.",
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
        [InlineKeyboardButton(text="📩 OTP yuborildi",callback_data=f"{prefix}:OTP_SENT"),
         InlineKeyboardButton(text="Kod qabul qilindi",callback_data=f"{prefix}:ACCEPT_CODE")],
        [InlineKeyboardButton(text="Kod noto‘g‘ri",callback_data=f"{prefix}:WRONG_CODE"),
         InlineKeyboardButton(text="Yangi kod yuboring",callback_data=f"{prefix}:RESEND_CODE")],
        [InlineKeyboardButton(text="Qabul qilish",callback_data=f"{prefix}:CLAIM"),
         InlineKeyboardButton(text="Coin topshirildi",callback_data=f"{prefix}:COMPLETE")],
        [InlineKeyboardButton(text="Xabar yozish",callback_data=f"{prefix}:WRITE"),
         InlineKeyboardButton(text="Rad etish",callback_data=f"{prefix}:REJECT")],
        [InlineKeyboardButton(text="🔐 Credentialni ochish",callback_data=f"{prefix}:CREDENTIALS")],
    ])


async def render(target, kind, order_id):
    result=await get_coin_chat(kind,order_id); messages=result.get("data",[])
    await mark_coin_chat_read(kind, order_id)
    transcript="\n\n".join(f"{'👤 User' if x.get('sender')=='USER' else '🛡 Operator'}:\n{x.get('message','')}" for x in messages[-10:]) or "Xabar yo‘q"
    await target.answer(f"💬 {kind} Coin Order #{order_id}\nStatus: {result.get('status','—')}\n\n{transcript}",reply_markup=keyboard(kind,order_id))


async def render_private(callback, kind, order_id):
    result=await get_coin_chat(kind,order_id); messages=result.get("data",[])
    await mark_coin_chat_read(kind, order_id)
    transcript="\n\n".join(f"{'👤 User' if x.get('sender')=='USER' else '🛡 Operator'}:\n{x.get('message','')}" for x in messages[-10:]) or "Xabar yo‘q"
    await callback.bot.send_message(callback.from_user.id,
        f"💬 {kind} Coin Order #{order_id}\nStatus: {result.get('status','—')}\n\n{transcript}",
        reply_markup=keyboard(kind,order_id), protect_content=True)


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
    _,kind,raw_id=callback.data.split(":"); await render_private(callback,kind,int(raw_id)); await callback.answer("Shaxsiy chatda ochildi")


@router.callback_query(F.data.startswith("coinchat:"))
async def quick(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): return await callback.answer("Ruxsat yo‘q",show_alert=True)
    _,kind,raw_id,action=callback.data.split(":"); order_id=int(raw_id)
    if action=="WRITE":
        await state.update_data(kind=kind,order_id=order_id); await state.set_state(CoinChatState.message)
        await callback.bot.send_message(callback.from_user.id,"Operator xabarini yozing:"); return await callback.answer()
    if action=="CREDENTIALS":
        result=await open_coin_credentials(kind,order_id,callback.from_user.id)
        if not result.get("success"): return await callback.answer(result.get("detail") or "Credential mavjud emas",show_alert=True)
        link=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="🔐 Bir martalik credential oynasi",web_app=WebAppInfo(url=result["view_url"]))
        ]])
        await callback.bot.send_message(callback.from_user.id,
            "Credential serverdagi bir martalik, 60 soniyalik oynada ochiladi.",
            reply_markup=link,
            protect_content=True,
        )
        return await callback.answer("Xavfsiz havola tayyor")
    result=await coin_chat_action(kind,order_id,callback.from_user.id,action)
    if not result.get("success"): return await callback.answer(result.get("detail") or result.get("message") or "Xatolik",show_alert=True)
    if action in QUICK and action != "OTP_SENT": await send_coin_chat_message(kind,order_id,callback.from_user.id,QUICK[action])
    await callback.answer("Yangilandi"); await render_private(callback,kind,order_id)


@router.message(CoinChatState.message)
async def operator_message(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    data=await state.get_data(); result=await send_coin_chat_message(data["kind"],data["order_id"],message.from_user.id,message.text or "")
    await state.clear(); await message.answer("Xabar yuborildi." if result.get("success") else "Xabar yuborilmadi.")
