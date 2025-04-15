import os
import logging
import requests
import re
from datetime import datetime
import pytz
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, CallbackQueryHandler, ConversationHandler, filters

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
FIREFLY_URL = os.getenv("FIREFLY_III_API_URL")
FIREFLY_TOKEN = os.getenv("FIREFLY_III_API_TOKEN")

SELECT_ORIGIN, ENTER_AMOUNT_DESC, SELECT_DESTINATION, ENTER_NEW_DEST_NAME = range(4)

OCULTAR_CUENTAS = ["WiseEmergency", "TrezorBtc"]
OCULTAR_CUENTAS_LOWER = [c.lower() for c in OCULTAR_CUENTAS]

logging.basicConfig(level=logging.WARNING, encoding='utf-8')

async def start_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("💼 Ver cuentas", callback_data="menu_assets")],
        [InlineKeyboardButton("💸 Registrar gasto", callback_data="menu_expense")],
        [InlineKeyboardButton("📊 Ver cuenta + movimientos", callback_data="menu_cuenta")],
        [InlineKeyboardButton("📋 Ver comandos", callback_data="menu_commands")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("❓ ¿Qué querés hacer?", reply_markup=reply_markup)

async def handle_menu_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "menu_assets":
        await list_assets(query, context)
    elif query.data == "menu_expense":
        await start_expense_button(update.callback_query, context)
    elif query.data == "menu_cuenta":
        await query.message.reply_text("Usá el comando:\n/cuenta <nombre> <N>")
    elif query.data == "menu_commands":
        await list_commands(query, context)

async def list_assets(update_or_query, context):
    headers = {"Authorization": f"Bearer {FIREFLY_TOKEN}"}
    try:
        response = requests.get(f"{FIREFLY_URL}/api/v1/accounts?type=asset", headers=headers)
        accounts = response.json().get("data", [])
        keyboard = []
        for a in accounts:
            name = a['attributes']['name']
            if name.lower() in OCULTAR_CUENTAS_LOWER:
                continue
            keyboard.append([InlineKeyboardButton(name, callback_data=f"cuenta::{name.lower()}")])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await update_or_query.message.reply_text("\U0001F4BC Tus cuentas de activo:", reply_markup=reply_markup)
    except Exception as e:
        logging.error(f"Error en list_assets: {e}")
        await update_or_query.message.reply_text("No se pudo obtener la lista de cuentas.")

async def show_account_from_callback(query, context, name):
    headers = {"Authorization": f"Bearer {FIREFLY_TOKEN}"}
    try:
        accounts = requests.get(f"{FIREFLY_URL}/api/v1/accounts", headers=headers).json()["data"]
        account_id = None
        balance = "0.00"
        for a in accounts:
            if a["attributes"]["name"].lower() == name.lower():
                account_id = a["id"]
                balance = a["attributes"].get("current_balance", "0.00")
                break

        if not account_id:
            await query.message.reply_text("Cuenta no encontrada.")
            return

        tx_url = f"{FIREFLY_URL}/api/v1/accounts/{account_id}/transactions?limit=3"
        txs = requests.get(tx_url, headers=headers).json()["data"]

        lines = [f"cuenta: {name}", f"balance: {float(balance):.2f}", "movimientos:"]
        for t in txs:
            for s in t["attributes"].get("transactions", []):
                fecha = s.get("date", "").split("T")[0]
                desc = s.get("description", "-")
                monto = float(s.get("amount", "0.00"))
                lines.append(f"{fecha} {desc} {monto:.2f}")

        await query.message.reply_text("\n".join(lines))
    except Exception as e:
        logging.error(f"Error en show_account_from_callback: {e}")
        await query.message.reply_text("No se pudo obtener la info de la cuenta.")

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data.startswith("cuenta::"):
        cuenta_name = data.replace("cuenta::", "")
        await show_account_from_callback(query, context, cuenta_name)
    elif data.startswith("menu_"):
        await handle_menu_selection(update, context)

async def show_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    parts = update.message.text.strip().split()
    if len(parts) < 2:
        await update.message.reply_text("Uso correcto: /cuenta <nombre> <N>")
        return
    name = parts[1]
    try:
        n = int(parts[2]) if len(parts) > 2 else 3
    except ValueError:
        await update.message.reply_text("Cantidad de movimientos inválida.")
        return

    headers = {"Authorization": f"Bearer {FIREFLY_TOKEN}"}
    try:
        accounts = requests.get(f"{FIREFLY_URL}/api/v1/accounts", headers=headers).json()["data"]
        account_id = None
        balance = "0.00"
        for a in accounts:
            if a["attributes"]["name"].lower() == name.lower():
                account_id = a["id"]
                balance = a["attributes"].get("current_balance", "0.00")
                break

        if not account_id:
            await update.message.reply_text("Cuenta no encontrada.")
            return

        tx_url = f"{FIREFLY_URL}/api/v1/accounts/{account_id}/transactions?limit={n}"
        txs = requests.get(tx_url, headers=headers).json()["data"]

        lines = [f"cuenta: {name}", f"balance: {float(balance):.2f}", "movimientos:"]
        for t in txs:
            for s in t["attributes"].get("transactions", []):
                fecha = s.get("date", "").split("T")[0]
                desc = s.get("description", "-")
                monto = float(s.get("amount", "0.00"))
                lines.append(f"{fecha} {desc} {monto:.2f}")

        await update.message.reply_text("\n".join(lines))
    except Exception as e:
        logging.error(f"Error en /cuenta: {e}")
        await update.message.reply_text("Error al obtener los datos de la cuenta.")

async def create_expense(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message.text
    logging.info(f"Mensaje recibido: {message}")
    if message == "/expense":
        await update.message.reply_text(
            "Uso correcto:\n/expense <monto> \"<descripción>\" <cuenta_origen> <cuenta_destino>\n"
            "Ejemplo:\n/expense 12.50 \"burger King\" wise comida"
        )
        return
    pattern = r'^/expense\s+([\d.,]+)\s+[\"“”]([^\"“”]+)[\"“”]\s+(\S+)(?:\s+(\S+))?$'
    match = re.match(pattern, message)

    if not match:
        await update.message.reply_text(
            "Uso correcto:\n/expense <monto> \"<descripción>\" <cuenta_origen> [<cuenta_destino>]\n"
            "Ejemplo:\n/expense 12.50 \"burger King\" wise comida"
        )
        return

    amount_str, description, source_name, destination_name = match.groups()

    try:
        amount = float(amount_str.replace(",", "."))
    except ValueError:
        await update.message.reply_text("Monto inválido.")
        return

    headers = {"Authorization": f"Bearer {FIREFLY_TOKEN}"}
    try:
        response = requests.get(f"{FIREFLY_URL}/api/v1/accounts", headers=headers)
        accounts = response.json().get("data", [])

        source_id = destination_id = None
        for a in accounts:
            name = a["attributes"]["name"].lower()
            if name == source_name.lower():
                source_id = a["id"]
            if destination_name and name == destination_name.lower():
                destination_id = a["id"]

        if not source_id:
            await update.message.reply_text("Cuenta de origen no encontrada.")
            return

        if destination_name and not destination_id:
            create_payload = {
                "name": destination_name,
                "type": "expense",
                "currency_id": 1
            }
            r = requests.post(f"{FIREFLY_URL}/api/v1/accounts", json=create_payload, headers=headers)
            r.raise_for_status()
            destination_id = r.json().get("data", {}).get("id")

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

        post_response = requests.post(f"{FIREFLY_URL}/api/v1/transactions", json=payload, headers=headers)
        post_response.raise_for_status()

        await update.message.reply_text(f"✅ Gasto registrado: {amount} - {description}")
    except Exception as e:
        logging.error(f"Error al registrar gasto: {e}")
        await update.message.reply_text("Error al registrar el gasto.")

# --- /expenseButtom INTERACTIVO ---
async def start_expense_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    headers = {"Authorization": f"Bearer {FIREFLY_TOKEN}"}
    response = requests.get(f"{FIREFLY_URL}/api/v1/accounts?type=asset", headers=headers)
    accounts = response.json().get("data", [])
    keyboard = []
    for a in accounts:
        name = a['attributes']['name']
        if name.lower() in OCULTAR_CUENTAS_LOWER:
            continue
        keyboard.append([InlineKeyboardButton(name, callback_data=f"origin::{name.lower()}")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.message:
        await update.message.reply_text("Seleccioná la cuenta de origen:", reply_markup=reply_markup)
    else:
        await update.callback_query.message.reply_text("Seleccioná la cuenta de origen:", reply_markup=reply_markup)

    return SELECT_ORIGIN

async def select_origin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['origin'] = query.data.replace("origin::", "")
    logging.info(f"👉 Entró al handler de SELECT_ORIGIN con origen: {context.user_data['origin']}")
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

    headers = {"Authorization": f"Bearer {FIREFLY_TOKEN}"}
    response = requests.get(f"{FIREFLY_URL}/api/v1/accounts?type=expense", headers=headers)
    accounts = response.json().get("data", [])
    keyboard = []
    for a in accounts:
        name = a['attributes']['name']
        keyboard.append([InlineKeyboardButton(name, callback_data=f"dest::{name.lower()}" )])
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
    return await create_transaction(query.message, context)

async def enter_new_dest_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new_dest_name = update.message.text.strip()
    headers = {"Authorization": f"Bearer {FIREFLY_TOKEN}"}
    create_payload = {
        "name": new_dest_name,
        "type": "expense",
        "currency_id": 1
    }
    r = requests.post(f"{FIREFLY_URL}/api/v1/accounts", json=create_payload, headers=headers)
    r.raise_for_status()
    destination_id = r.json().get("data", {}).get("id")
    context.user_data['destination_id'] = destination_id
    return await create_transaction(update.message, context)

async def create_transaction(message_source, context):
    headers = {"Authorization": f"Bearer {FIREFLY_TOKEN}"}
    accounts = requests.get(f"{FIREFLY_URL}/api/v1/accounts", headers=headers).json().get("data", [])
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

    post_response = requests.post(f"{FIREFLY_URL}/api/v1/transactions", json=payload, headers=headers)
    post_response.raise_for_status()

    await message_source.reply_text("✅ Gasto creado correctamente")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Operación cancelada.")
    return ConversationHandler.END
# Fin expense interactivo
async def debug_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    logging.warning(f"🧪 Recibido callback: {query.data}")
    await query.message.reply_text(f"Recibido: {query.data}")

# --- NUEVO: Comando /commands ---
async def list_commands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    commands = [
        "/start - Muestra el menú principal",
        "/menu - Muestra el menú de opciones",
        "/assets - Lista tus cuentas de activo",
        "/cuenta <nombre> <N> - Muestra movimientos de una cuenta",
        "/expense - Crea un gasto (manual)",
        "/expenseButtom - Crea un gasto con botones",
        "/cancel - Cancela un flujo activo"
    ]
    await update.message.reply_text("Comandos disponibles:\n" + "\n".join(commands))

if __name__ == '__main__':
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start_menu))
    app.add_handler(CommandHandler("menu", start_menu))
    app.add_handler(CommandHandler("cuenta", show_account))
    app.add_handler(CommandHandler("assets", list_assets))
    app.add_handler(CommandHandler("commands", list_commands))

    app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'^/expense.*'), create_expense))

    expense_conv = ConversationHandler(
        entry_points=[
            CommandHandler("expenseButtom", start_expense_button),
            CallbackQueryHandler(start_expense_button, pattern="^menu_expense$")
        ],
        states={
            SELECT_ORIGIN: [CallbackQueryHandler(select_origin)],
            ENTER_AMOUNT_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_amount_description)],
            SELECT_DESTINATION: [CallbackQueryHandler(select_destination, pattern=r"^dest::")],
            ENTER_NEW_DEST_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_new_dest_name)]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_chat=True  # ✅ SOLO este
    )

    app.add_handler(expense_conv)
    app.add_handler(CallbackQueryHandler(handle_callback))

    app.run_polling()
