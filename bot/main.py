import logging
from telegram.ext import ApplicationBuilder
from bot.config import TELEGRAM_TOKEN, LOG_LEVEL
from bot.handlers.menu import menu_handlers
from bot.handlers.expense import expense_handlers
from bot.handlers.account import account_handlers
from bot.handlers.assets import assets_handlers

# Configuración de logs
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.WARNING),
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    encoding="utf-8"
)

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # Handlers generales
    for handler in menu_handlers + expense_handlers + account_handlers + assets_handlers:
        app.add_handler(handler)

    app.run_polling()

if __name__ == '__main__':
    main()
