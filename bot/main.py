import logging
from telegram.ext import ApplicationBuilder, CallbackQueryHandler
from bot.config import TELEGRAM_TOKEN, LOG_LEVEL
from bot.handlers.menu import menu_handlers
from bot.handlers.expense import expense_handlers
from bot.handlers.account import account_handlers, handle_callback
from bot.handlers.assets import assets_handlers

# Configuración de logs
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.WARNING),
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    encoding="utf-8"
)

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # Primero, registrar todos los handlers de flujo (ConversationHandlers, etc.)
    for handler in menu_handlers + expense_handlers + account_handlers + assets_handlers:
        app.add_handler(handler)

    # Luego, agregar el handler catch-all de callback queries (cuentas, menú, etc.)
    app.add_handler(CallbackQueryHandler(handle_callback))

    app.run_polling()

if __name__ == '__main__':
    main()
