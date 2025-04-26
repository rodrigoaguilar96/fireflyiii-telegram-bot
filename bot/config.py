import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
FIREFLY_URL = os.getenv("FIREFLY_III_API_URL")
FIREFLY_TOKEN = os.getenv("FIREFLY_III_API_TOKEN")
LOG_LEVEL = os.getenv("LOG_LEVEL", "WARNING").upper()

#cuentas a ocultar
HIDE_ACCOUNTS = os.getenv("HIDE_ACCOUNTS", "")
OCULTAR_CUENTAS = [c.strip() for c in HIDE_ACCOUNTS.split(",") if c.strip()]
OCULTAR_CUENTAS_LOWER = [c.lower() for c in OCULTAR_CUENTAS]