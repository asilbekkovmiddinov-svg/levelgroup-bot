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
    card_number: str,
    card_holder: str,
    bank_name: str,
):
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{BACKEND_URL}/withdraw/create",
            json={
                "telegram_id": telegram_id,
                "amount": amount,
                "card_number": card_number,
                "card_holder": card_holder,
                "bank_name": bank_name,
            },
        ) as response:
            return await safe_json(response)


async def claim_deposit(deposit_id: int, admin_id: int):
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{BACKEND_URL}/deposit/{deposit_id}/claim",
            json={"admin_id": admin_id},
        ) as response:
            return await safe_json(response)


async def claim_withdraw(withdraw_id: int, admin_id: int):
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{BACKEND_URL}/withdraw/{withdraw_id}/claim",
            params={"admin_id": admin_id},
        ) as response:
            return await safe_json(response)


async def approve_deposit(deposit_id: int, admin_id: int):
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{BACKEND_URL}/deposit/{deposit_id}/approve",
            json={"admin_id": admin_id},
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


async def approve_withdraw(withdraw_id: int, admin_id: int):
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{BACKEND_URL}/withdraw/approve/{withdraw_id}",
            params={"admin_id": admin_id},
        ) as response:
            return await safe_json(response)


async def reject_withdraw(withdraw_id: int, admin_id: int):
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{BACKEND_URL}/withdraw/reject/{withdraw_id}",
            params={"admin_id": admin_id},
        ) as response:
            return await safe_json(response)
async def create_p2p_order(
    telegram_id: int,
    efc_amount: float,
    price_uzs: float,
):
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{BACKEND_URL}/p2p/create",
            json={
                "telegram_id": telegram_id,
                "efc_amount": efc_amount,
                "price_uzs": price_uzs,
            },
        ) as response:
            return await safe_json(response)


async def get_open_p2p_orders():
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{BACKEND_URL}/p2p/open"
        ) as response:
            if response.status != 200:
                return []

            return await safe_json(response)


async def get_p2p_order(order_id: int):
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{BACKEND_URL}/p2p/{order_id}"
        ) as response:
            return await safe_json(response)


async def reserve_p2p_order(order_id: int, telegram_id: int):
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{BACKEND_URL}/p2p/{order_id}/reserve",
            json={"telegram_id": telegram_id},
        ) as response:
            return await safe_json(response)


async def complete_p2p_order(order_id: int, telegram_id: int):
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{BACKEND_URL}/p2p/{order_id}/complete",
            json={"telegram_id": telegram_id},
        ) as response:
            return await safe_json(response)


async def cancel_p2p_order(order_id: int, telegram_id: int):
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{BACKEND_URL}/p2p/{order_id}/cancel",
            json={"telegram_id": telegram_id},
        ) as response:
            return await safe_json(response)
