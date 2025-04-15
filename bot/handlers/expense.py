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
        keyboard.append([InlineKeyboardButton(name, callback_data=f"origin::{name.lower()}")])

    reply_markup = InlineKeyboardMarkup(
        keyboard + [[InlineKeyboardButton("❌ Cancelar", callback_data="cancelar")]]
    )

    if update.message:
        await update.message.reply_text("Seleccioná la cuenta de origen:", reply_markup=reply_markup)
    else:
        await update.callback_query.message.reply_text("Seleccioná la cuenta de origen:", reply_markup=reply_markup)

    logging.warning("🧪 En start_expense_button: mostrando cuentas de origen")
    return SELECT_ORIGIN

async def select_origin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.warning(f"🧪 Entró a select_origin con callback: {update.callback_query.data}")
    query = update.callback_query
    await query.answer()
    context.user_data['origin'] = query.data.replace("origin::", "")
    await query.message.reply_text(
        "Ahora escribí el monto y la descripción.\nEjemplo: 13.99 hamburguesa",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancelar", callback_data="cancelar")]])
    )
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

    reply_markup = InlineKeyboardMarkup(
        keyboard + [[InlineKeyboardButton("❌ Cancelar", callback_data="cancelar")]]
    )
    await update.message.reply_text("Seleccioná cuenta de destino (opcional):", reply_markup=reply_markup)
    return SELECT_DESTINATION

async def select_destination(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    dest = query.data.replace("dest::", "")

    if dest == "new":
        await query.message.reply_text(
            "Escribí el nombre de la nueva cuenta de destino:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancelar", callback_data="cancelar")]])
        )
        return ENTER_NEW_DEST_NAME

    context.user_data['destination'] = dest
    return await create_expense_transaction(query.message, context)

async def enter_new_dest_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new_dest_name = update.message.text.strip()
    try:
        result = create_account(new_dest_name)
        result.raise_for_status()
        destination_id = result.json().get("data", {}).get("id")
        context.user_data['destination_id'] = destination_id
        return await create_expense_transaction(update.message, context)
    except Exception as e:
        logging.error(f"Error creando nueva cuenta: {e}")
        await update.message.reply_text("No se pudo crear la nueva cuenta.")
        return ConversationHandler.END

async def create_expense_transaction(message_source, context):
    accounts = get_accounts()
    source_id = destination_id = None

    for a in accounts:
        name = a["attributes"]["name"].lower()
        if name == context.user_data.get('origin'):
            source_id = a["id"]
        if name == context.user_data.get('destination'):
            destination_id = a["id"]

    if 'destination_id' in context.user_data:
        destination_id = context.user_data['destination_id']

    if not source_id:
        await message_source.reply_text("❌ Cuenta de origen no encontrada.")
        return ConversationHandler.END

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

    try:
        response = create_transaction(payload)
        response.raise_for_status()
        await message_source.reply_text("✅ Gasto creado correctamente")
    except Exception as e:
        logging.error(f"Error al crear transacción: {e}")
        await message_source.reply_text("❌ Error al registrar el gasto.")
    return ConversationHandler.END

async def quick_expense(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        args = context.args
        if len(args) < 3:
            await update.message.reply_text("Uso: /expense <monto> \"<desc>\" <origen> [<destino>]")
            return

        amount = float(args[0].replace(',', '.'))
        description = args[1].strip('"')
        origin = args[2].lower()
        destination = args[3].lower() if len(args) > 3 else None

        accounts = get_accounts()
        source_id = destination_id = None

        for a in accounts:
            name = a["attributes"]["name"].lower()
            if name == origin:
                source_id = a["id"]
            if destination and name == destination:
                destination_id = a["id"]

        if not source_id:
            await update.message.reply_text("❌ Cuenta de origen no encontrada.")
            return

        if destination and not destination_id:
            try:
                result = create_account(destination)
                result.raise_for_status()
                destination_id = result.json().get("data", {}).get("id")
            except Exception as e:
                logging.error(f"Error creando cuenta destino '{destination}': {e}")
                await update.message.reply_text("❌ No se pudo crear la cuenta de destino.")
                return

        today = datetime.now(pytz.timezone("Europe/Lisbon")).isoformat()
        payload = {
            "transactions": [
                {
                    "type": "withdrawal",
                    "amount": str(amount),
                    "description": description,
                    "source_id": source_id,
                    "destination_id": destination_id,
                    "date": today
                }
            ]
        }

        response = create_transaction(payload)
        response.raise_for_status()
        await update.message.reply_text("✅ Gasto creado correctamente")
    except Exception as e:
        logging.error(f"Error en /expense: {e}")
        await update.message.reply_text("❌ Error al procesar el gasto.")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.warning("⚠️ Entró a cancel()")
    if update.message:
        await update.message.reply_text("❌ Operación cancelada.")
    elif update.callback_query:
        await update.callback_query.message.reply_text("❌ Operación cancelada.")
    return ConversationHandler.END

expense_conv = ConversationHandler(
    entry_points=[
        CommandHandler("expenseButtom", start_expense_button),
        CallbackQueryHandler(start_expense_button, pattern="^menu_expense$")
    ],
    states={
        SELECT_ORIGIN: [CallbackQueryHandler(select_origin, pattern="^origin::")],
        ENTER_AMOUNT_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_amount_description)],
        SELECT_DESTINATION: [CallbackQueryHandler(select_destination, pattern="^dest::")],
        ENTER_NEW_DEST_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_new_dest_name)]
    },
    fallbacks=[
        CommandHandler("cancel", cancel),
        CallbackQueryHandler(cancel, pattern="^cancelar$")
    ],
    per_chat=True
)

expense_handlers = [
    CommandHandler("expense", quick_expense),
    expense_conv
]