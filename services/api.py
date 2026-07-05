import aiohttp

from config import BACKEND_URL


async def safe_json(response):
    try:
        return await response.json()
    except Exception:
        return {"message": "Backend error"}


async def get_wallet(telegram_id: int):
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{BACKEND_URL}/wallet/{telegram_id}"
        ) as response:
            if response.status != 200:
                return None

            return await safe_json(response)


async def get_products():
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{BACKEND_URL}/products/active"
        ) as response:
            if response.status != 200:
                return []

            return await safe_json(response)


async def create_order(
    telegram_id: int,
    product_id: int,
):
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{BACKEND_URL}/orders/create",
            json={
                "telegram_id": telegram_id,
                "product_id": product_id,
            },
        ) as response:
            return await safe_json(response)


async def create_deposit(
    telegram_id: int,
    amount: int,
):
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{BACKEND_URL}/deposit/create",
            json={
                "telegram_id": telegram_id,
                "amount": amount,
            },
        ) as response:
            return await safe_json(response)


async def create_withdraw(
    telegram_id: int,
    amount: int,
):
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{BACKEND_URL}/withdraw/create",
            json={
                "telegram_id": telegram_id,
                "amount": amount,
            },
        ) as response:
            return await safe_json(response)


async def claim_deposit(
    deposit_id: int,
    admin_id: int,
):
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{BACKEND_URL}/deposit/{deposit_id}/claim",
            json={
                "admin_id": admin_id,
            },
        ) as response:
            return await safe_json(response)
async def approve_deposit(
    deposit_id: int,
    admin_id: int,
):
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{BACKEND_URL}/deposit/{deposit_id}/approve",
            json={
                "admin_id": admin_id,
            },
        ) as response:
            return await safe_json(response)


async def reject_deposit(
    deposit_id: int,
    admin_id: int,
    reason: str = "Admin rad etdi",
):
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{BACKEND_URL}/deposit/{deposit_id}/reject",
            json={
                "admin_id": admin_id,
                "reason": reason,
            },
        ) as response:
            return await safe_json(response)


async def approve_withdraw(
    withdraw_id: int,
    admin_id: int,
):
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{BACKEND_URL}/withdraw/approve/{withdraw_id}",
            params={
                "admin_id": admin_id,
            },
        ) as response:
            return await safe_json(response)


async def reject_withdraw(
    withdraw_id: int,
    admin_id: int,
):
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{BACKEND_URL}/withdraw/reject/{withdraw_id}",
            params={
                "admin_id": admin_id,
            },
        ) as response:
            return await safe_json(response)
