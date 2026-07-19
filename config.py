import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
BACKEND_URL = os.getenv("BACKEND_URL")

# Arena API foundation. User requests use verified Telegram MiniApp initData;
# worker/admin requests use the backend's separate internal authentication.
ARENA_API_URL = os.getenv("ARENA_API_URL", BACKEND_URL or "").rstrip("/")
ARENA_API_TIMEOUT_SECONDS = float(os.getenv("ARENA_API_TIMEOUT_SECONDS", "10"))
ARENA_API_RETRIES = max(0, int(os.getenv("ARENA_API_RETRIES", "2")))
ARENA_API_RETRY_BACKOFF_SECONDS = float(
    os.getenv("ARENA_API_RETRY_BACKOFF_SECONDS", "0.25")
)
INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY")
CAMPAIGN_DELIVERY_INTERVAL_SECONDS = float(os.getenv("CAMPAIGN_DELIVERY_INTERVAL_SECONDS", "5"))
CAMPAIGN_DELIVERY_RATE_DELAY_SECONDS = float(os.getenv("CAMPAIGN_DELIVERY_RATE_DELAY_SECONDS", "0.05"))
CAMPAIGN_DELIVERY_RATE_LIMIT_RETRIES = int(os.getenv("CAMPAIGN_DELIVERY_RATE_LIMIT_RETRIES", "5"))
CAMPAIGN_DELIVERY_BACKOFF_SECONDS = float(os.getenv("CAMPAIGN_DELIVERY_BACKOFF_SECONDS", "1"))
CAMPAIGN_MINIAPP_URL = (os.getenv("CAMPAIGN_MINIAPP_URL") or os.getenv("MINIAPP_URL") or "").strip()

if CAMPAIGN_DELIVERY_INTERVAL_SECONDS <= 0:
    raise ValueError("CAMPAIGN_DELIVERY_INTERVAL_SECONDS must be positive")
if CAMPAIGN_DELIVERY_RATE_DELAY_SECONDS < 0:
    raise ValueError("CAMPAIGN_DELIVERY_RATE_DELAY_SECONDS cannot be negative")
if CAMPAIGN_DELIVERY_RATE_LIMIT_RETRIES < 0 or CAMPAIGN_DELIVERY_BACKOFF_SECONDS <= 0:
    raise ValueError("Invalid campaign delivery retry configuration")
ARENA_MINIAPP_URL = os.getenv("ARENA_MINIAPP_URL") or os.getenv("MINIAPP_URL")
ARENA_EVIDENCE_STATE_DB = os.getenv("ARENA_EVIDENCE_STATE_DB", "levelgroup.db")

NEW_ORDERS_CHANNEL_ID = int(os.getenv("NEW_ORDERS_CHANNEL_ID", "0"))
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0"))
ADMIN_USER_IDS = {
    int(value.strip())
    for value in os.getenv("ADMIN_USER_IDS", "").split(",")
    if value.strip()
}
ADMIN_LOGS_CHANNEL_ID = int(os.getenv("ADMIN_LOGS_CHANNEL_ID", "0"))
COMPLETED_ORDERS_CHANNEL_ID = int(os.getenv("COMPLETED_ORDERS_CHANNEL_ID", "0"))

# 1vs1 Arena
MATCH_RESULTS_CHANNEL_ID = int(
    os.getenv("MATCH_RESULTS_CHANNEL_ID", "0")
)
