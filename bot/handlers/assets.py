import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CommandHandler, ContextTypes
from bot.config import OCULTAR_CUENTAS_LOWER
from bot.client import get_accounts

async def list_assets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        accounts = get_accounts(account_type="asset")
        keyboard = []

        for a in accounts:
            name = a['attributes']['name']
            if name.lower() in OCULTAR_CUENTAS_LOWER:
                continue
            keyboard.append([InlineKeyboardButton(name, callback_data=f"cuenta::{name.lower()}")])

        if keyboard:
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("💼 Tus cuentas de activo:", reply_markup=reply_markup)
        else:
            await update.message.reply_text("No hay cuentas visibles para mostrar.")

    except Exception as e:
        logging.error(f"Error en list_assets: {e}")
        await update.message.reply_text("No se pudo obtener la lista de cuentas.")

assets_handlers = [
    CommandHandler("assets", list_assets)
]
