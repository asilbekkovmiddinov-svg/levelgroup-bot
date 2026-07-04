import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
BACKEND_URL = os.getenv("BACKEND_URL")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN topilmadi!")

if not BACKEND_URL:
    raise ValueError("BACKEND_URL topilmadi!")
