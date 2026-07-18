import asyncio

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import BOT_TOKEN

from handlers.start import router as start_router
from handlers.wallet import router as wallet_router
from handlers.deposit import router as deposit_router
from handlers.withdraw import router as withdraw_router
from handlers.p2p import router as p2p_router
from handlers.wheel import router as wheel_router
from handlers.admin_wheel import router as admin_wheel_router
from handlers.chat_id import router as chat_id_router
from handlers.admin_orders import router as admin_orders_router
from handlers.match import router as match_router
from handlers.admin_match import router as admin_match_router
from handlers.admin_coin_chat import router as admin_coin_chat_router
from handlers.admin_coin_shop import router as admin_coin_shop_router

from middlewares.user_seen import UserSeenMiddleware
from services.api import check_p2p_timeouts
from services.match_api import (
    finish_ready_check,
    get_due_scheduled_matches,
    get_expired_ready_matches,
    start_ready_check,
)
from services.arena_notifications import ArenaNotification, send_arena_notification


bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(
        parse_mode=ParseMode.HTML,
    ),
)

dp = Dispatcher()

dp.message.middleware(UserSeenMiddleware())
dp.callback_query.middleware(UserSeenMiddleware())

dp.include_router(start_router)
dp.include_router(wallet_router)
dp.include_router(deposit_router)
dp.include_router(withdraw_router)
dp.include_router(p2p_router)
dp.include_router(wheel_router)
dp.include_router(admin_wheel_router)
dp.include_router(chat_id_router)
dp.include_router(admin_orders_router)
dp.include_router(match_router)
dp.include_router(admin_match_router)
dp.include_router(admin_coin_chat_router)
dp.include_router(admin_coin_shop_router)


async def p2p_timeout_worker():
    await asyncio.sleep(5)

    while True:
        try:
            result = await check_p2p_timeouts()

            if isinstance(result, dict) and result.get("success"):
                trades = result.get("data", [])

                for trade in trades:
                    trade_id = trade.get("id")
                    owner_id = trade.get("owner_id")
                    requester_id = trade.get("requester_id")
                    reason = trade.get("cancel_reason") or "Savdo vaqti tugadi"

                    text = (
                        "⏰ P2P savdo vaqti tugadi.\n\n"
                        f"🆔 Trade: #{trade_id}\n"
                        f"📌 Sabab: {reason}\n\n"
                        "Locked balans avtomatik qaytarildi."
                    )

                    for user_id in [owner_id, requester_id]:
                        try:
                            await bot.send_message(
                                chat_id=user_id,
                                text=text,
                            )
                        except Exception:
                            pass

        except Exception as error:
            print(f"P2P timeout worker error: {error}")

        await asyncio.sleep(10)


async def arena_ready_start_worker():
    await asyncio.sleep(10)

    while True:
        try:
            data = await get_due_scheduled_matches(limit=50)
            matches = data.get("matches", [])

            for match in matches:
                try:
                    updated_match = await start_ready_check(match["id"])

                    for user_id in [
                        updated_match["creator_telegram_id"],
                        updated_match["opponent_telegram_id"],
                    ]:
                        if user_id:
                            await send_arena_notification(
                                bot,
                                user_id,
                                ArenaNotification.READY_REQUIRED,
                                match_id=updated_match["id"],
                                amount=updated_match["efc_amount"],
                                detail="Tayyorlikni 5 daqiqa ichida MiniApp’da tasdiqlang.",
                            )

                except Exception:
                    print("Arena ready start item failed")

        except Exception:
            print("Arena ready start worker failed")

        await asyncio.sleep(10)


async def arena_ready_finish_worker():
    await asyncio.sleep(15)

    while True:
        try:
            data = await get_expired_ready_matches(limit=50)
            matches = data.get("matches", [])

            for match in matches:
                try:
                    updated_match = await finish_ready_check(match["id"])

                    status = updated_match["status"]

                    if status == "ROOM_READY":
                        notification = ArenaNotification.ROOM_CODE_READY
                        detail = "Ikkala o‘yinchi ham tayyor. Creator Room Code kiritishi mumkin."
                    elif status == "TECHNICAL_REVIEW":
                        notification = ArenaNotification.TECHNICAL_REVIEW
                        detail = "Admin texnik holatni ko‘rib chiqadi."
                    elif status == "CANCELLED":
                        notification = ArenaNotification.CANCELLED
                        detail = "Tayyorlik tasdiqlanmadi. Locked EFC balansga qaytarildi."
                    else:
                        notification = ArenaNotification.READY_EXPIRED
                        detail = "Match holati yangilandi."

                    for user_id in [
                        updated_match["creator_telegram_id"],
                        updated_match["opponent_telegram_id"],
                    ]:
                        if user_id:
                            await send_arena_notification(
                                bot,
                                user_id,
                                notification,
                                match_id=updated_match["id"],
                                detail=detail,
                            )

                except Exception:
                    print("Arena ready finish item failed")

        except Exception:
            print("Arena ready finish worker failed")

        await asyncio.sleep(10)


async def main():
    print("🚀 LEVEL_GROUP Bot ishga tushdi...")

    asyncio.create_task(p2p_timeout_worker())
    asyncio.create_task(arena_ready_start_worker())
    asyncio.create_task(arena_ready_finish_worker())

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
