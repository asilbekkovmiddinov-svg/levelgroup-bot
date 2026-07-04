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
