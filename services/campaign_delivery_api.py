import aiohttp

from config import BACKEND_URL, INTERNAL_API_KEY


class CampaignDeliveryApiError(RuntimeError):
    pass


class CampaignDeliveryApi:
    def __init__(self, base_url=BACKEND_URL, internal_api_key=INTERNAL_API_KEY, session_factory=aiohttp.ClientSession):
        self.base_url = (base_url or "").rstrip("/")
        self.internal_api_key = internal_api_key
        self.session_factory = session_factory

    def _headers(self):
        if not self.base_url:
            raise CampaignDeliveryApiError("BACKEND_URL is not configured")
        if not self.internal_api_key:
            raise CampaignDeliveryApiError("INTERNAL_API_KEY is not configured")
        return {"X-Internal-Api-Key": self.internal_api_key}

    async def _post(self, path: str, payload: dict | None = None):
        async with self.session_factory() as session:
            async with session.post(
                f"{self.base_url}{path}", headers=self._headers(), json=payload,
            ) as response:
                if response.status < 200 or response.status >= 300:
                    raise CampaignDeliveryApiError(f"Internal Delivery API returned HTTP {response.status}")
                try:
                    return await response.json()
                except (aiohttp.ContentTypeError, ValueError) as error:
                    raise CampaignDeliveryApiError("Internal Delivery API returned invalid JSON") from error

    async def claim(self) -> list[dict]:
        result = await self._post("/internal/campaigns/recipients/claim")
        if not isinstance(result, list):
            raise CampaignDeliveryApiError("Invalid claim response")
        return result

    async def sent(self, recipient_id: int, claimed_at: str, delivery_time: float):
        return await self._post(
            f"/internal/campaigns/recipients/{recipient_id}/sent",
            {"claimed_at": claimed_at, "delivery_time": max(0.0, delivery_time)},
        )

    async def failed(self, recipient_id: int, claimed_at: str, reason: str, temporary: bool, delivery_time: float):
        return await self._post(
            f"/internal/campaigns/recipients/{recipient_id}/failed",
            {
                "claimed_at": claimed_at, "failure_reason": reason[:500],
                "temporary": temporary, "delivery_time": max(0.0, delivery_time),
            },
        )

    async def recalculate(self, campaign_id: int):
        return await self._post(f"/internal/campaigns/{campaign_id}/recalculate")
