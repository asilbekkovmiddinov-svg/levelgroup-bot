import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
BACKEND_URL = os.getenv("BACKEND_URL")

NEW_ORDERS_CHANNEL_ID = int(os.getenv("NEW_ORDERS_CHANNEL_ID", "0"))
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0"))
ADMIN_LOGS_CHANNEL_ID = int(os.getenv("ADMIN_LOGS_CHANNEL_ID", "0"))
COMPLETED_ORDERS_CHANNEL_ID = int(os.getenv("COMPLETED_ORDERS_CHANNEL_ID", "0"))
