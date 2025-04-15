from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, MessageHandler, ConversationHandler, ContextTypes, filters
from datetime import datetime
import pytz
import logging
from bot.client import get_accounts, create_transaction, create_account
from bot.constants import SELECT_ORIGIN, ENTER_AMOUNT_DESC, SELECT_DESTINATION, ENTER_NEW_DEST_NAME
from bot.config import OCULTAR_CUENTAS_LOWER

async def start_expense_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    accounts = get_accounts(account_type="asset")
    keyboard = []
    for a in accounts:
        name = a['attributes']['name']
        if name.lower() in OCULTAR_CUENTAS_LOWER:
            continue
        keyboard.append([InlineKeyboardButton(name, callback_data=f"origin::{name.lower()}" )])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Seleccioná la cuenta de origen:", reply_markup=reply_markup)
    return SELECT_ORIGIN

async def select_origin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['origin'] = query.data.replace("origin::", "")
    await query.message.reply_text("Ahora escribí el monto y la descripción.\nEjemplo: 13.99 hamburguesa")
    return ENTER_AMOUNT_DESC

async def enter_amount_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    try:
        amount_str, *description_parts = text.split()
        amount = float(amount_str.replace(',', '.'))
        description = ' '.join(description_parts)
    except:
        await update.message.reply_text("Formato inválido. Usá: 13.99 hamburguesa")
        return ENTER_AMOUNT_DESC

    context.user_data['amount'] = amount
    context.user_data['description'] = description

    accounts = get_accounts(account_type="expense")
    keyboard = []
    for a in accounts:
        name = a['attributes']['name']
        keyboard.append([InlineKeyboardButton(name, callback_data=f"dest::{name.lower()}")])
    keyboard.append([InlineKeyboardButton("➕ Crear nueva cuenta", callback_data="dest::new")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Seleccioná cuenta de destino (opcional):", reply_markup=reply_markup)
    return SELECT_DESTINATION

async def select_destination(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    dest = query.data.replace("dest::", "")

    if dest == "new":
        await query.message.reply_text("Escribí el nombre de la nueva cuenta de destino:")
        return ENTER_NEW_DEST_NAME

    context.user_data['destination'] = dest
    return await create_expense_transaction(query.message, context)

async def enter_new_dest_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new_dest_name = update.message.text.strip()
    result = create_account(new_dest_name)
    result.raise_for_status()
    destination_id = result.json().get("data", {}).get("id")
    context.user_data['destination_id'] = destination_id
    return await create_expense_transaction(update.message, context)

async def create_expense_transaction(message_source, context):
    accounts = get_accounts()
    source_id = destination_id = None

    for a in accounts:
        name = a["attributes"]["name"].lower()
        if name == context.user_data['origin']:
            source_id = a["id"]
        if 'destination' in context.user_data and name == context.user_data['destination']:
            destination_id = a["id"]

    if 'destination_id' in context.user_data:
        destination_id = context.user_data['destination_id']

    today = datetime.now(pytz.timezone("Europe/Lisbon")).isoformat()
    payload = {
        "transactions": [
            {
                "type": "withdrawal",
                "amount": str(context.user_data['amount']),
                "description": context.user_data['description'],
                "source_id": source_id,
                "destination_id": destination_id,
                "date": today
            }
        ]
    }

    create_transaction(payload)
    await message_source.reply_text("✅ Gasto creado correctamente")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Operación cancelada.")
    return ConversationHandler.END

expense_handlers = [
    CommandHandler("expenseButtom", start_expense_button),
    CallbackQueryHandler(start_expense_button, pattern="^menu_expense$"),
    ConversationHandler(
        entry_points=[CallbackQueryHandler(start_expense_button, pattern="^menu_expense$")],
        states={
            SELECT_ORIGIN: [CallbackQueryHandler(select_origin)],
            ENTER_AMOUNT_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_amount_description)],
            SELECT_DESTINATION: [CallbackQueryHandler(select_destination, pattern=r"^dest::")],
            ENTER_NEW_DEST_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_new_dest_name)]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_chat=True
    )
]
