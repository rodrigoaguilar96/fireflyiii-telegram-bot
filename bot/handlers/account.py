import logging
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes, CallbackQueryHandler

from bot.client import get_accounts, safe_get
from bot.handlers.common import format_account_display
from bot.handlers.menu import handle_menu_selection


async def show_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show account info and recent transactions via /cuenta command."""
    parts = update.message.text.strip().split()
    if len(parts) < 2:
        await update.message.reply_text("Uso: /cuenta <nombre> [N]")
        return

    name = parts[1]
    try:
        n = int(parts[2]) if len(parts) > 2 else 3
    except ValueError:
        await update.message.reply_text("Cantidad de movimientos inválida.")
        return

    result = await format_account_display(name, limit=n)
    if result:
        # Split long messages (Telegram limit: 4096 chars)
        for chunk in _split_message(result):
            await update.message.reply_text(chunk, parse_mode="Markdown")
    else:
        await update.message.reply_text("Cuenta no encontrada.")


async def show_account_from_callback(query, context, name):
    """Show account info from a callback query button."""
    result = await format_account_display(name, limit=3)
    if result:
        for chunk in _split_message(result):
            await query.message.reply_text(chunk, parse_mode="Markdown")
    else:
        await query.message.reply_text("Cuenta no encontrada.")


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Catch-all callback handler for non-conversation callbacks."""
    query = update.callback_query
    await query.answer()
    data = query.data

    # Ignore callbacks reserved for ConversationHandlers
    if data.startswith((
        "origin::",
        "dest::",
        "cat::",
        "budget::",
        "cancelar",
        "transfer_source::",
        "transfer_destination::",
    )) or data in ("confirm_transfer", "cancel_transfer"):
        logging.debug(f"Ignoring reserved callback: {data}")
        return

    logging.debug(f"Handling callback: {data}")

    if data.startswith("cuenta::"):
        cuenta_name = data.replace("cuenta::", "")
        await show_account_from_callback(query, context, cuenta_name)
    elif data.startswith("menu_"):
        await handle_menu_selection(update, context)


def _split_message(text: str, max_length: int = 4000) -> list[str]:
    """Split a message into chunks that fit within Telegram's limit."""
    if len(text) <= max_length:
        return [text]
    chunks = []
    while text:
        if len(text) <= max_length:
            chunks.append(text)
            break
        # Split at last newline before max_length
        split_at = text.rfind("\n", 0, max_length)
        if split_at == -1:
            split_at = max_length
        chunks.append(text[:split_at])
        text = text[split_at:].lstrip("\n")
    return chunks


account_handlers = [
    CommandHandler("cuenta", show_account),
    CallbackQueryHandler(handle_callback, pattern="^cuenta::")
]
