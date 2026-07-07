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

from middlewares.user_seen import UserSeenMiddleware


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


async def main():
    print("🚀 LEVEL_GROUP Bot ishga tushdi...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
