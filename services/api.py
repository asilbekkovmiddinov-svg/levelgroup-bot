import aiohttp

from config import BACKEND_URL


async def get_wallet(telegram_id: int):
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{BACKEND_URL}/wallet/{telegram_id}"
        ) as response:
            if response.status != 200:
                return None

            return await response.json()
async def get_products():
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{BACKEND_URL}/products/active"
        ) as response:
            if response.status != 200:
                return []

            return await response.json()

async def create_order(telegram_id: int, product_id: int):
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{BACKEND_URL}/orders/create",
            json={
                "telegram_id": telegram_id,
                "product_id": product_id
            }
        ) as response:
            return await response.json()
            
async def create_deposit(telegram_id: int, amount: int):
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{BACKEND_URL}/deposit/create",
            json={
                "telegram_id": telegram_id,
                "amount": amount
            }
        ) as response:
            return await response.json()
