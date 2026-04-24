from telegram import InlineKeyboardMarkup, InlineKeyboardButton, Update
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes

from bot.handlers.common import list_commands
from bot.handlers.assets import list_assets
from bot.middleware import require_auth


async def start_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_auth(update, context):
        return

    keyboard = [
        [InlineKeyboardButton("💸 Registrar gasto", callback_data="menu_expense")],
        [InlineKeyboardButton("💼 Ver cuentas", callback_data="menu_assets")],
        [InlineKeyboardButton("📊 Ver cuenta + movimientos", callback_data="menu_cuenta")],
        [InlineKeyboardButton("📋 Ver comandos", callback_data="menu_commands")]
    ]
    await update.message.reply_text("¿Qué querés hacer?", reply_markup=InlineKeyboardMarkup(keyboard))


async def handle_menu_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "menu_assets":
        await list_assets(query, context)
    elif data == "menu_cuenta":
        await query.message.reply_text(
            "Elegí una cuenta para ver saldo y movimientos:"
        )
        await list_assets(query, context)
    elif data == "menu_commands":
        await list_commands(query, context)


menu_handlers = [
    CommandHandler("start", start_menu),
    CommandHandler("menu", start_menu),
    # `menu_expense` is intentionally handled by the expense ConversationHandler.
    # If this generic menu handler consumes it first, the expense flow displays
    # the account buttons but never enters SELECT_ORIGIN.
    CallbackQueryHandler(handle_menu_selection, pattern="^(menu_assets|menu_cuenta|menu_commands)$")
]
