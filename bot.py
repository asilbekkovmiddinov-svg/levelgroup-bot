import asyncio

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import BOT_TOKEN

from handlers.start import router as start_router
from handlers.wallet import router as wallet_router
from handlers.buy import router as buy_router
from handlers.deposit import router as deposit_router
from handlers.withdraw import router as withdraw_router
from handlers.p2p import router as p2p_router
from handlers.wheel import router as wheel_router
from handlers.admin_wheel import router as admin_wheel_router
from handlers.chat_id import router as chat_id_router
from handlers.admin_orders import router as admin_orders_router
from handlers.match import router as match_router

from middlewares.user_seen import UserSeenMiddleware
from services.api import check_p2p_timeouts


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
dp.include_router(buy_router)
dp.include_router(deposit_router)
dp.include_router(withdraw_router)
dp.include_router(p2p_router)
dp.include_router(wheel_router)
dp.include_router(admin_wheel_router)
dp.include_router(chat_id_router)
dp.include_router(admin_orders_router)
dp.include_router(match_router)


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


async def main():
    print("🚀 LEVEL_GROUP Bot ishga tushdi...")

    asyncio.create_task(p2p_timeout_worker())

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
