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
ARENA_MINIAPP_URL = os.getenv("ARENA_MINIAPP_URL") or os.getenv("MINIAPP_URL")

NEW_ORDERS_CHANNEL_ID = int(os.getenv("NEW_ORDERS_CHANNEL_ID", "0"))
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0"))
ADMIN_LOGS_CHANNEL_ID = int(os.getenv("ADMIN_LOGS_CHANNEL_ID", "0"))
COMPLETED_ORDERS_CHANNEL_ID = int(os.getenv("COMPLETED_ORDERS_CHANNEL_ID", "0"))

# 1vs1 Arena
MATCH_RESULTS_CHANNEL_ID = int(
    os.getenv("MATCH_RESULTS_CHANNEL_ID", "0")
)
