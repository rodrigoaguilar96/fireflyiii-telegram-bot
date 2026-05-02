import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CommandHandler, ContextTypes

from bot.config import OCULTAR_CUENTAS_LOWER
from bot.client import get_accounts
from bot.middleware import require_auth


async def list_assets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List asset accounts from the /assets command."""
    if not await require_auth(update, context):
        return

    await show_assets(update, context)


async def show_assets(update_or_query, context: ContextTypes.DEFAULT_TYPE):
    """List asset accounts, callable after auth from message or callback query."""
    try:
        accounts = get_accounts(account_type="asset")
        keyboard = []

        for a in accounts:
            name = a['attributes']['name']
            if name.lower() in OCULTAR_CUENTAS_LOWER:
                continue
            keyboard.append(
                [InlineKeyboardButton(name, callback_data=f"cuenta::{name.lower()}")]
            )

        if keyboard:
            reply_markup = InlineKeyboardMarkup(keyboard)
            if hasattr(update_or_query, 'message') and update_or_query.message:
                await update_or_query.message.reply_text(
                    "💼 Tus cuentas de activo:", reply_markup=reply_markup
                )
            else:
                await update_or_query.callback_query.message.reply_text(
                    "💼 Tus cuentas de activo:", reply_markup=reply_markup
                )
        else:
            msg = "No hay cuentas visibles para mostrar."
            if hasattr(update_or_query, 'message') and update_or_query.message:
                await update_or_query.message.reply_text(msg)
            else:
                await update_or_query.callback_query.message.reply_text(msg)

    except Exception as e:
        logging.error(f"Error en list_assets: {e}")
        msg = "No se pudo obtener la lista de cuentas."
        if hasattr(update_or_query, 'message') and update_or_query.message:
            await update_or_query.message.reply_text(msg)
        else:
            await update_or_query.callback_query.message.reply_text(msg)


assets_handlers = [
    CommandHandler("assets", list_assets)
]
