import logging
import sys

from telegram.ext import ApplicationBuilder, CallbackQueryHandler

from bot.config import TELEGRAM_TOKEN, LOG_LEVEL, validate_env
from bot.handlers.menu import menu_handlers
from bot.handlers.expense import expense_handlers
from bot.handlers.transfer import transfer_handlers
from bot.handlers.account import account_handlers, handle_callback
from bot.handlers.assets import assets_handlers
from bot.middleware import require_auth

# Configuración de logs
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.WARNING),
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    encoding="utf-8"
)

logger = logging.getLogger(__name__)


def _validate_startup():
    """Validate required environment variables before starting."""
    missing = validate_env()
    if missing:
        logger.critical(
            f"Missing required environment variables: {', '.join(missing)}"
        )
        sys.exit(1)
    logger.info("Environment validation passed")


def main():
    _validate_startup()

    logger.info("Starting Firefly III Telegram Bot...")
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # Register all conversation handlers first
    for handler in menu_handlers + expense_handlers + transfer_handlers + account_handlers + assets_handlers:
        app.add_handler(handler)

    # Catch-all callback handler (must be last)
    app.add_handler(CallbackQueryHandler(handle_callback))

    logger.info("Bot started successfully")
    app.run_polling()


if __name__ == '__main__':
    main()
