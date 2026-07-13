import aiohttp

from config import BACKEND_URL, INTERNAL_API_KEY


def internal_headers():
    if not INTERNAL_API_KEY:
        raise RuntimeError("INTERNAL_API_KEY sozlanmagan")
    return {"X-Internal-Api-Key": INTERNAL_API_KEY}


async def safe_json(response):
    try:
        return await response.json()
    except Exception:
        return {"success": False, "message": "Backend error"}


async def get_wallet(telegram_id: int):
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{BACKEND_URL}/internal/wallet/{telegram_id}",
            headers=internal_headers(),
        ) as response:
            if response.status != 200:
                return None
            return await safe_json(response)


async def update_user_seen(telegram_id: int):
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{BACKEND_URL}/internal/users/{telegram_id}/seen",
            headers=internal_headers(),
        ) as response:
            return await safe_json(response)


async def register_internal_user(
    telegram_id: int,
    username: str | None = None,
    first_name: str | None = None,
    last_name: str | None = None,
):
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{BACKEND_URL}/internal/users/register",
            headers=internal_headers(),
            json={
                "telegram_id": telegram_id,
                "username": username,
                "first_name": first_name,
                "last_name": last_name,
            },
        ) as response:
            return await safe_json(response)


async def get_products():
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{BACKEND_URL}/products/active") as response:
            if response.status != 200:
                return []
            return await safe_json(response)


async def create_order(telegram_id: int, product_id: int):
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{BACKEND_URL}/orders/create",
            json={
                "telegram_id": telegram_id,
                "product_id": product_id,
            },
        ) as response:
            return await safe_json(response)


async def create_deposit(telegram_id: int, amount: int):
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


async def claim_withdraw(withdraw_id: int, admin_id: int):
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{BACKEND_URL}/withdraw/{withdraw_id}/claim",
            params={"admin_id": admin_id},
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
    order_type: str,
    efc_amount: float,
    price_uzs: float,
    min_trade_efc: float,
    response_minutes: int,
):
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{BACKEND_URL}/p2p/create",
            json={
                "telegram_id": telegram_id,
                "order_type": order_type,
                "efc_amount": efc_amount,
                "price_uzs": price_uzs,
                "min_trade_efc": min_trade_efc,
                "response_minutes": response_minutes,
            },
        ) as response:
            return await safe_json(response)


async def get_open_p2p_orders(order_type: str | None = None):
    params = {}
    if order_type:
        params["order_type"] = order_type

    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{BACKEND_URL}/p2p/open",
            params=params,
        ) as response:
            if response.status != 200:
                return []
            return await safe_json(response)


async def get_p2p_order(order_id: int):
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{BACKEND_URL}/p2p/{order_id}") as response:
            return await safe_json(response)
async def create_p2p_trade(
    order_id: int,
    telegram_id: int,
    efc_amount: float,
):
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{BACKEND_URL}/p2p/{order_id}/trade",
            json={
                "telegram_id": telegram_id,
                "efc_amount": efc_amount,
            },
        ) as response:
            return await safe_json(response)


async def approve_p2p_trade(trade_id: int, telegram_id: int):
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{BACKEND_URL}/p2p/trade/{trade_id}/approve",
            json={"telegram_id": telegram_id},
        ) as response:
            return await safe_json(response)


async def reject_p2p_trade(trade_id: int, telegram_id: int):
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{BACKEND_URL}/p2p/trade/{trade_id}/reject",
            json={"telegram_id": telegram_id},
        ) as response:
            return await safe_json(response)


async def confirm_p2p_trade(trade_id: int, telegram_id: int):
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{BACKEND_URL}/p2p/trade/{trade_id}/confirm",
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


async def get_my_p2p_orders(telegram_id: int):
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{BACKEND_URL}/p2p/my/{telegram_id}"
        ) as response:
            if response.status != 200:
                return []
            return await safe_json(response)


async def get_my_p2p_trades(telegram_id: int):
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{BACKEND_URL}/p2p/trades/my/{telegram_id}"
        ) as response:
            if response.status != 200:
                return []
            return await safe_json(response)


async def update_p2p_order_price(
    order_id: int,
    telegram_id: int,
    price_uzs: float,
):
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{BACKEND_URL}/p2p/{order_id}/update-price",
            json={
                "telegram_id": telegram_id,
                "price_uzs": price_uzs,
            },
        ) as response:
            return await safe_json(response)


async def update_p2p_order_amount(
    order_id: int,
    telegram_id: int,
    efc_amount: float,
):
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{BACKEND_URL}/p2p/{order_id}/update-amount",
            json={
                "telegram_id": telegram_id,
                "efc_amount": efc_amount,
            },
        ) as response:
            return await safe_json(response)


async def update_p2p_order_min_trade(
    order_id: int,
    telegram_id: int,
    min_trade_efc: float,
):
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{BACKEND_URL}/p2p/{order_id}/update-min-trade",
            json={
                "telegram_id": telegram_id,
                "min_trade_efc": min_trade_efc,
            },
        ) as response:
            return await safe_json(response)


async def update_p2p_order_response_minutes(
    order_id: int,
    telegram_id: int,
    response_minutes: int,
):
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{BACKEND_URL}/p2p/{order_id}/update-response-minutes",
            json={
                "telegram_id": telegram_id,
                "response_minutes": response_minutes,
            },
        ) as response:
            return await safe_json(response)


async def get_p2p_history(
    telegram_id: int,
    status: str | None = None,
):
    params = {}

    if status:
        params["status"] = status

    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{BACKEND_URL}/p2p/history/{telegram_id}",
            params=params,
        ) as response:
            if response.status != 200:
                return []
            return await safe_json(response)


async def check_p2p_timeouts():
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{BACKEND_URL}/p2p/timeouts/check"
        ) as response:
            return await safe_json(response)


async def get_wheel_status(telegram_id: int):
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{BACKEND_URL}/wheel/status/{telegram_id}"
        ) as response:
            return await safe_json(response)


async def spin_wheel(
    telegram_id: int,
    spin_type: str,
):
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{BACKEND_URL}/wheel/spin",
            json={
                "telegram_id": telegram_id,
                "spin_type": spin_type,
            },
        ) as response:
            return await safe_json(response)


async def fill_wheel_coin_order(
    telegram_id: int,
    spin_id: int,
    konami_login: str,
    konami_password: str,
    region: str,
    device: str,
):
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{BACKEND_URL}/wheel/coin-order/details",
            json={
                "telegram_id": telegram_id,
                "spin_id": spin_id,
                "konami_login": konami_login,
                "konami_password": konami_password,
                "region": region,
                "device": device,
            },
        ) as response:
            return await safe_json(response)
async def approve_wheel_coin_order(
    order_id: int,
    admin_id: int,
):
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{BACKEND_URL}/wheel/coin-orders/{order_id}/approve",
            params={
                "admin_id": admin_id,
            },
        ) as response:
            return await safe_json(response)


async def reject_wheel_coin_order(
    order_id: int,
    admin_id: int,
    reason: str = "Admin rad etdi",
):
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{BACKEND_URL}/wheel/coin-orders/{order_id}/reject",
            params={
                "admin_id": admin_id,
                "reason": reason,
            },
        ) as response:
            return await safe_json(response)
