import asyncio

import aiohttp

from config import BACKEND_URL, INTERNAL_API_KEY


REQUEST_TIMEOUT_SECONDS = 15

STATUS_MESSAGES = {
    400: "So‘rov ma’lumotlari yoki balans yetarli emas.",
    401: "Backend autentifikatsiyani rad etdi.",
    403: "Bu amal uchun ruxsat yo‘q.",
    404: "So‘rov topilmadi.",
    409: "So‘rov holati o‘zgargan. Yangilab qayta urinib ko‘ring.",
    422: "Yuborilgan ma’lumotlar noto‘g‘ri.",
    500: "Backendda ichki xatolik yuz berdi.",
}


async def safe_json(response):
    try:
        return await response.json()
    except Exception:
        return {"success": False, "message": "Backend error"}


def internal_headers():
    if not INTERNAL_API_KEY:
        return None
    return {"X-Internal-Api-Key": INTERNAL_API_KEY}


async def wallet_request(method: str, path: str, **kwargs):
    headers = internal_headers()
    if not headers:
        return {
            "success": False,
            "status_code": 500,
            "message": "INTERNAL_API_KEY bot sozlamasida yo‘q.",
        }

    timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT_SECONDS)
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.request(
                method,
                f"{BACKEND_URL}{path}",
                headers=headers,
                **kwargs,
            ) as response:
                data = await safe_json(response)
    except asyncio.TimeoutError:
        return {
            "success": False,
            "status_code": 504,
            "message": "Backend javobi kutilgan vaqtdan oshdi.",
        }
    except aiohttp.ClientError:
        return {
            "success": False,
            "status_code": 503,
            "message": "Backend bilan tarmoq aloqasi uzildi.",
        }

    if not isinstance(data, dict):
        data = {"message": "Backend noto‘g‘ri javob qaytardi."}

    data["status_code"] = response.status
    data["success"] = 200 <= response.status < 300
    if response.status >= 400:
        data["message"] = data.get("message") or data.get("detail") or STATUS_MESSAGES.get(
            response.status,
            "Backend so‘rovni bajarmadi.",
        )
    return data


async def get_wallet(telegram_id: int):
    result = await wallet_request("GET", f"/internal/wallet/{telegram_id}")

    if result.get("status_code") == 403:
        result["message"] = "Internal API key noto‘g‘ri yoki sozlanmagan."
    elif result.get("status_code") == 404:
        result["message"] = "Foydalanuvchi yoki wallet topilmadi."

    return result


async def update_user_seen(telegram_id: int):
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{BACKEND_URL}/user/{telegram_id}/seen"
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
    return await wallet_request(
        "POST",
        "/deposit/create",
        json={"telegram_id": telegram_id, "amount": amount},
    )


async def create_withdraw(
    telegram_id: int,
    amount: int,
    card_number: str,
    card_holder: str,
    bank_name: str,
):
    return await wallet_request(
        "POST",
        "/internal/withdraw/create",
        json={
            "telegram_id": telegram_id,
            "amount": amount,
            "card_number": card_number,
            "card_holder": card_holder,
            "bank_name": bank_name,
        },
    )


async def claim_deposit(deposit_id: int, admin_id: int):
    return await wallet_request(
        "POST",
        f"/deposit/{deposit_id}/claim",
        json={"admin_id": admin_id},
    )


async def approve_deposit(deposit_id: int, admin_id: int):
    return await wallet_request(
        "POST",
        f"/deposit/{deposit_id}/approve",
        json={"admin_id": admin_id},
    )
async def reject_deposit(
    deposit_id: int,
    admin_id: int,
    reason: str = "Admin rad etdi",
):
    return await wallet_request(
        "POST",
        f"/deposit/{deposit_id}/reject",
        json={"admin_id": admin_id, "reason": reason},
    )


async def claim_withdraw(withdraw_id: int, admin_id: int):
    return await wallet_request(
        "POST",
        f"/withdraw/{withdraw_id}/claim",
        params={"admin_id": admin_id},
    )


async def approve_withdraw(withdraw_id: int, admin_id: int):
    return await wallet_request(
        "POST",
        f"/withdraw/approve/{withdraw_id}",
        params={"admin_id": admin_id},
    )


async def reject_withdraw(withdraw_id: int, admin_id: int, reason: str = "Admin rad etdi"):
    return await wallet_request(
        "POST",
        f"/withdraw/reject/{withdraw_id}",
        params={"admin_id": admin_id, "reason": reason},
    )


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
