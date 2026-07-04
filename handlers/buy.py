from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from services.api import get_products, create_order

router = Router()


@router.message(F.text == "🛒 Coin sotib olish")
async def buy_coins(message: Message):
    products = await get_products()

    if not products:
        await message.answer("❌ Hozircha mahsulotlar topilmadi.")
        return

    for product in products:
        text = (
            f"🪙 <b>{product['title']}</b>\n\n"
            f"🎮 Platforma: {product.get('platform') or '-'}\n"
            f"🌍 Region: {product.get('region') or '-'}\n"
            f"🪙 Coins: {product['coins_amount']}\n"
            f"💵 Narx: {product['price_uzs']} so'm"
        )

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✅ Sotib olish",
                        callback_data=f"buy_{product['id']}"
                    )
                ]
            ]
        )

        await message.answer(text, reply_markup=keyboard)


@router.callback_query(F.data.startswith("buy_"))
async def buy_product(callback: CallbackQuery):
    product_id = int(callback.data.replace("buy_", ""))

    result = await create_order(
        telegram_id=callback.from_user.id,
        product_id=product_id
    )

    if result.get("message") == "Insufficient balance":
        await callback.message.answer("❌ Balansingiz yetarli emas.")
        await callback.answer()
        return

    if result.get("message") == "Order created":
        await callback.message.answer(
            "✅ Buyurtma yaratildi!\n\n"
            f"📦 Buyurtma ID: {result['order_id']}\n"
            f"🪙 Paket: {result['product_title']}\n"
            f"💵 Narx: {result['price_uzs']} so'm\n"
            f"📌 Status: {result['status']}"
        )
        await callback.answer()
        return

    await callback.message.answer("❌ Buyurtma yaratishda xatolik yuz berdi.")
    await callback.answer()
