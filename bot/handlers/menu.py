from telegram import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    Update,
)
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from bot.handlers.common import list_commands
from bot.handlers.assets import show_assets
from bot.handlers import subscriptions
from bot.constants import (
    EXPENSE_BUTTON_TEXT,
    MENU_BUTTON_PATTERN,
    MENU_BUTTON_TEXT,
)
from bot.middleware import require_auth


def main_reply_keyboard():
    """Return the persistent keyboard for the most common bot actions."""
    return ReplyKeyboardMarkup(
        [[MENU_BUTTON_TEXT, EXPENSE_BUTTON_TEXT]],
        resize_keyboard=True,
        is_persistent=True,
    )


async def start_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_auth(update, context):
        return

    keyboard = [
        [InlineKeyboardButton(EXPENSE_BUTTON_TEXT, callback_data="menu_expense")],
        [InlineKeyboardButton("💰 Registrar ingreso", callback_data="menu_income")],
        [InlineKeyboardButton("🔁 Transferir", callback_data="menu_transfer")],
        [InlineKeyboardButton("💼 Ver cuentas", callback_data="menu_assets")],
        [InlineKeyboardButton("📊 Ver cuenta + movimientos", callback_data="menu_cuenta")],
        [InlineKeyboardButton("🧾 Suscripciones pendientes", callback_data="menu_subscriptions")],
        [InlineKeyboardButton("📋 Ver comandos", callback_data="menu_commands")]
    ]
    await update.message.reply_text(
        "Accesos rápidos disponibles abajo 👇",
        reply_markup=main_reply_keyboard(),
    )
    await update.message.reply_text(
        "¿Qué querés hacer?",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def cancel_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """End an active conversation and show the main menu."""
    context.user_data.clear()
    await start_menu(update, context)
    return ConversationHandler.END


async def handle_menu_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_auth(update, context):
        return

    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "menu_assets":
        await show_assets(update, context)
    elif data == "menu_cuenta":
        await query.message.reply_text(
            "Elegí una cuenta para ver saldo y movimientos:"
        )
        await show_assets(update, context)
    elif data == "menu_commands":
        await list_commands(query, context)
    elif data == "menu_subscriptions":
        await subscriptions.show_current_period_subscriptions(update, context)


menu_handlers = [
    CommandHandler("start", start_menu),
    CommandHandler("menu", start_menu),
    MessageHandler(filters.Regex(MENU_BUTTON_PATTERN), start_menu),
    # `menu_expense`, `menu_income`, and `menu_transfer` are intentionally handled by
    # ConversationHandlers so the dedicated flows own their state transitions.
    CallbackQueryHandler(handle_menu_selection, pattern="^(menu_assets|menu_cuenta|menu_commands|menu_subscriptions)$")
]
