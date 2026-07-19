import asyncio
import html
import logging
import time
from dataclasses import dataclass
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from aiogram.exceptions import (
    TelegramBadRequest, TelegramForbiddenError, TelegramNetworkError,
    TelegramRetryAfter, TelegramServerError,
)
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

from config import (
    CAMPAIGN_DELIVERY_BACKOFF_SECONDS, CAMPAIGN_DELIVERY_INTERVAL_SECONDS,
    CAMPAIGN_DELIVERY_RATE_DELAY_SECONDS, CAMPAIGN_DELIVERY_RATE_LIMIT_RETRIES,
    CAMPAIGN_MINIAPP_URL,
)
from services.campaign_delivery_api import CampaignDeliveryApi


logger = logging.getLogger(__name__)
TEMPORARY_ERRORS = (TelegramNetworkError, TelegramServerError)
PERMANENT_ERRORS = (TelegramForbiddenError, TelegramBadRequest)
ACTION_PAGES = {
    "COIN_SHOP": "coinShop", "REFERRAL": "referral", "ARENA": "arena",
    "WHEEL": "wheel", "PROFILE": "profile",
}


def _miniapp_url(page: str | None = None, **values) -> str | None:
    if not CAMPAIGN_MINIAPP_URL:
        return None
    parts = urlsplit(CAMPAIGN_MINIAPP_URL)
    if parts.scheme != "https" or not parts.netloc:
        return None
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    if page:
        query["page"] = page
    query.update({key: str(value) for key, value in values.items() if value is not None})
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def notification_keyboard(recipient: dict) -> InlineKeyboardMarkup | None:
    text = (recipient.get("button_text") or "Ochish").strip()
    action = str(recipient.get("button_action") or "NONE").upper()
    target = (recipient.get("button_target") or "").strip()
    if action == "NONE":
        return None
    if action == "URL" and target.startswith(("https://", "http://")):
        button = InlineKeyboardButton(text=text, url=target)
    else:
        if recipient.get("promotion_id"):
            url = _miniapp_url("promotions", promotion_id=recipient["promotion_id"])
        elif action in ACTION_PAGES:
            url = _miniapp_url(ACTION_PAGES[action])
        elif action == "CUSTOM" and target.startswith(("https://", "http://")):
            url = target
            button = InlineKeyboardButton(text=text, url=url)
            return InlineKeyboardMarkup(inline_keyboard=[[button]])
        else:
            url = _miniapp_url("home", action=action, target=target or None)
        if not url:
            logger.warning("campaign_delivery_button_skipped action=%s reason=missing_miniapp_url", action)
            return None
        button = InlineKeyboardButton(text=text, web_app=WebAppInfo(url=url))
    return InlineKeyboardMarkup(inline_keyboard=[[button]])


def notification_text(recipient: dict) -> str:
    title = html.escape(str(recipient.get("title") or ""))
    message = html.escape(str(recipient.get("message") or ""))
    return f"<b>{title}</b>\n\n{message}".strip()


async def send_notification(bot, recipient: dict) -> None:
    text = notification_text(recipient)
    markup = notification_keyboard(recipient)
    image_url = recipient.get("image_url")
    if image_url and len(text) <= 1024:
        await bot.send_photo(chat_id=recipient["telegram_id"], photo=image_url, caption=text, reply_markup=markup)
    elif image_url:
        await bot.send_photo(chat_id=recipient["telegram_id"], photo=image_url)
        await bot.send_message(chat_id=recipient["telegram_id"], text=text, reply_markup=markup)
    else:
        await bot.send_message(chat_id=recipient["telegram_id"], text=text, reply_markup=markup)


@dataclass
class BatchResult:
    claimed: int = 0
    sent: int = 0
    failed: int = 0
    retries: int = 0


class CampaignDeliveryWorker:
    def __init__(
        self, bot, api: CampaignDeliveryApi | None = None,
        interval_seconds: float = CAMPAIGN_DELIVERY_INTERVAL_SECONDS,
        rate_delay_seconds: float = CAMPAIGN_DELIVERY_RATE_DELAY_SECONDS,
        rate_limit_retries: int = CAMPAIGN_DELIVERY_RATE_LIMIT_RETRIES,
        backoff_seconds: float = CAMPAIGN_DELIVERY_BACKOFF_SECONDS,
        sleep=asyncio.sleep, clock=time.monotonic,
    ):
        self.bot = bot
        self.api = api or CampaignDeliveryApi()
        self.interval_seconds = interval_seconds
        self.rate_delay_seconds = rate_delay_seconds
        self.rate_limit_retries = rate_limit_retries
        self.backoff_seconds = backoff_seconds
        self.sleep = sleep
        self.clock = clock

    async def _send_with_rate_limit(self, recipient: dict) -> int:
        retries = 0
        while True:
            try:
                await send_notification(self.bot, recipient)
                return retries
            except TelegramRetryAfter as error:
                if retries >= self.rate_limit_retries:
                    raise
                delay = max(float(error.retry_after), self.backoff_seconds * (2 ** retries))
                retries += 1
                logger.warning(
                    "campaign_delivery_retry recipient_id=%s retry_count=%s delay_seconds=%.3f",
                    recipient["recipient_id"], retries, delay,
                )
                await self.sleep(delay)

    async def process_batch(self) -> BatchResult:
        started = self.clock()
        logger.info("campaign_delivery_batch_start")
        recipients = await self.api.claim()
        result = BatchResult(claimed=len(recipients))
        if not recipients:
            logger.info(
                "campaign_delivery_batch_finish recipients_processed=0 sent=0 failed=0 retries=0 execution_seconds=%.6f",
                self.clock() - started,
            )
            return result
        logger.info("campaign_delivery_claimed recipients=%s", len(recipients))
        campaign_ids = set()
        for index, recipient in enumerate(recipients):
            item_started = self.clock()
            campaign_ids.add(int(recipient["campaign_id"]))
            try:
                retries = await self._send_with_rate_limit(recipient)
                result.retries += retries
            except Exception as error:
                temporary = isinstance(error, (TEMPORARY_ERRORS, TelegramRetryAfter)) or not isinstance(error, PERMANENT_ERRORS)
                reason = type(error).__name__
                try:
                    callback = await self.api.failed(
                        int(recipient["recipient_id"]), recipient["claimed_at"], reason,
                        temporary, self.clock() - item_started,
                    )
                    if callback.get("final"):
                        result.failed += 1
                    else:
                        result.retries += 1
                    logger.warning(
                        "campaign_delivery_failed recipient_id=%s temporary=%s retry_count=%s",
                        recipient["recipient_id"], temporary, callback.get("retry_count"),
                    )
                except Exception:
                    logger.exception("campaign_delivery_failed_callback recipient_id=%s", recipient["recipient_id"])
            else:
                try:
                    # A lost SENT callback must not be converted into a delivery failure:
                    # the active claim remains recoverable through the backend claim TTL.
                    await self.api.sent(
                        int(recipient["recipient_id"]), recipient["claimed_at"],
                        self.clock() - item_started,
                    )
                except Exception:
                    logger.exception("campaign_delivery_sent_callback recipient_id=%s", recipient["recipient_id"])
                else:
                    result.sent += 1
                    logger.info("campaign_delivery_sent recipient_id=%s", recipient["recipient_id"])
            if index + 1 < len(recipients) and self.rate_delay_seconds:
                await self.sleep(self.rate_delay_seconds)
        for campaign_id in sorted(campaign_ids):
            try:
                await self.api.recalculate(campaign_id)
            except Exception:
                logger.exception("campaign_delivery_statistics_failed campaign_id=%s", campaign_id)
        logger.info(
            "campaign_delivery_batch_finish recipients_processed=%s sent=%s failed=%s retries=%s execution_seconds=%.6f",
            result.claimed, result.sent, result.failed, result.retries, self.clock() - started,
        )
        return result

    async def run(self) -> None:
        logger.info("campaign_delivery_worker_started interval_seconds=%s", self.interval_seconds)
        while True:
            try:
                await self.process_batch()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("campaign_delivery_batch_failed")
            await self.sleep(self.interval_seconds)
