import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
FIREFLY_URL = os.getenv("FIREFLY_III_API_URL")
FIREFLY_TOKEN = os.getenv("FIREFLY_III_API_TOKEN")
LOG_LEVEL = os.getenv("LOG_LEVEL", "WARNING").upper()

# Cuentas a ocultar (solo desde env)
HIDE_ACCOUNTS = os.getenv("HIDE_ACCOUNTS", "")
OCULTAR_CUENTAS = [c.strip() for c in HIDE_ACCOUNTS.split(",") if c.strip()]
OCULTAR_CUENTAS_LOWER = [c.lower() for c in OCULTAR_CUENTAS]

# Usuarios autorizados (opcional — si vacío, acceso abierto)
ALLOWED_USER_IDS_RAW = os.getenv("ALLOWED_USER_IDS", "")
ALLOWED_USER_IDS = [
    int(x.strip()) for x in ALLOWED_USER_IDS_RAW.split(",") if x.strip()
]

# Zona horaria por defecto
TIMEZONE = os.getenv("TIMEZONE", "Europe/Lisbon")

# Variables requeridas
REQUIRED_ENV_VARS = {
    "TELEGRAM_BOT_TOKEN": TELEGRAM_TOKEN,
    "FIREFLY_III_API_URL": FIREFLY_URL,
    "FIREFLY_III_API_TOKEN": FIREFLY_TOKEN,
}


def validate_env() -> list[str]:
    """Return list of missing required environment variables."""
    return [name for name, value in REQUIRED_ENV_VARS.items() if not value]
