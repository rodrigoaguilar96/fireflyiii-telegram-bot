import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
FIREFLY_URL = os.getenv("FIREFLY_III_API_URL")
FIREFLY_TOKEN = os.getenv("FIREFLY_III_API_TOKEN")
HIDE_ACCOUNTS = os.getenv("HIDE_ACCOUNTS", "")
LOG_LEVEL = os.getenv("LOG_LEVEL", "WARNING").upper()
