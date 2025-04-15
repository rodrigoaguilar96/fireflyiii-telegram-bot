import os
import logging
import requests
import re
from datetime import date, datetime
import pytz
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters, CallbackQueryHandler

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
FIREFLY_URL = os.getenv("FIREFLY_III_API_URL")
FIREFLY_TOKEN = os.getenv("FIREFLY_III_API_TOKEN")

# Lista de cuentas que no queremos mostrar en /assets (insensible a mayúsculas)
OCULTAR_CUENTAS = ["WiseEmergency", "TrezorBtc"]
OCULTAR_CUENTAS_LOWER = [c.lower() for c in OCULTAR_CUENTAS]

logging.basicConfig(level=logging.WARNING)

async def list_assets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    headers = {
        "Authorization": f"Bearer {FIREFLY_TOKEN}"
    }
    try:
        response = requests.get(f"{FIREFLY_URL}/api/v1/accounts?type=asset", headers=headers)
        response.raise_for_status()
        accounts = response.json().get("data", [])

        keyboard = []
        for a in accounts:
            name = a['attributes']['name']
            name_lower = name.lower()
            if name_lower in OCULTAR_CUENTAS_LOWER:
                continue
            keyboard.append([InlineKeyboardButton(name, callback_data=f"cuenta::{name_lower}" )])

        if not keyboard:
            await update.message.reply_text("No hay cuentas visibles de tipo 'asset'.")
            return

        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("💼 Tus cuentas de activo:", reply_markup=reply_markup)

    except requests.RequestException as e:
        logging.error(f"Error al consultar Firefly III: {e}")
        await update.message.reply_text("No se pudo obtener la lista de cuentas.")


async def create_expense(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message.text
    logging.info(f"💬 Mensaje recibido: {message}")

    pattern = r'^/expense\s+([\d.,]+)\s+[\"“”]([^\"“”]+)[\"“”]\s+(\S+)\s+(\S+)$'
    match = re.match(pattern, message)

    if not match:
        logging.warning(f"❌ Regex no matcheó para: {message}")
        await update.message.reply_text(
            "Uso correcto:\n/expense <monto> \"<descripción>\" <cuenta_origen> <cuenta_destino>\n\n"
            "Ejemplo:\n/expense 12.50 \"burger King\" wise comida"
        )
        return

    amount_str, description, source_name, destination_name = match.groups()

    try:
        amount = float(amount_str.replace(",", "."))
    except ValueError:
        await update.message.reply_text("❌ Monto inválido.")
        return

    headers = {
        "Authorization": f"Bearer {FIREFLY_TOKEN}"
    }

    try:
        response = requests.get(f"{FIREFLY_URL}/api/v1/accounts", headers=headers)
        response.raise_for_status()
        accounts = response.json().get("data", [])

        source_id = None
        destination_id = None

        for a in accounts:
            name = a['attributes']['name'].lower()
            if name == source_name.lower():
                source_id = a['id']
            if name == destination_name.lower():
                destination_id = a['id']

        if not source_id or not destination_id:
            await update.message.reply_text("❌ No se encontraron las cuentas indicadas.")
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

        post_response = requests.post(f"{FIREFLY_URL}/api/v1/transactions", json=payload, headers=headers)
        post_response.raise_for_status()

        await update.message.reply_text(f"✅ Gasto registrado: {amount} - {description}")

    except requests.RequestException as e:
        logging.error(f"Error al crear gasto: {e}")
        await update.message.reply_text("❌ Error al registrar el gasto.")


async def show_account(update: Update, context: ContextTypes.DEFAULT_TYPE, name_arg=None):
    name = name_arg if name_arg else update.message.text.split()[1]
    n = 3

    headers = {
        "Authorization": f"Bearer {FIREFLY_TOKEN}"
    }

    try:
        accounts = requests.get(f"{FIREFLY_URL}/api/v1/accounts", headers=headers).json()["data"]
        account_id = None
        account_balance = "0.00"
        for a in accounts:
            if a["attributes"]["name"].lower() == name.lower():
                account_id = a["id"]
                account_balance = a["attributes"].get("current_balance", "0.00")
                break

        if not account_id:
            await update.message.reply_text("Cuenta no encontrada.")
            return

        tx_url = f"{FIREFLY_URL}/api/v1/accounts/{account_id}/transactions?limit={n}"
        tx_response = requests.get(tx_url, headers=headers)
        tx_response.raise_for_status()
        transactions = tx_response.json().get("data", [])

        lines = [f"cuenta: {name}", f"balance: {float(account_balance):.2f}", "movimientos:"]
        for t in transactions:
            for split in t["attributes"].get("transactions", []):
                raw_date = split.get("date", "-")
                date_str = raw_date.split("T")[0] if "T" in raw_date else raw_date
                desc = split.get("description", "-")
                amt = float(split.get("amount", "0.00"))
                lines.append(f"{date_str} {desc} {amt:.2f}")

        await update.message.reply_text("\n".join(lines))

    except Exception as e:
        logging.error(f"Error en /cuenta: {e}")
        await update.message.reply_text("Error al obtener los datos de la cuenta.")


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("cuenta::"):
        cuenta_name = data.replace("cuenta::", "")
        # Reutilizamos show_account pero pasándole el chat_id directo
        await show_account_from_callback(query, context, cuenta_name)



async def show_account_from_callback(query, context, name):
    headers = {
        "Authorization": f"Bearer {FIREFLY_TOKEN}"
    }
    try:
        accounts = requests.get(f"{FIREFLY_URL}/api/v1/accounts", headers=headers).json()["data"]
        account_id = None
        account_balance = "0.00"
        for a in accounts:
            if a["attributes"]["name"].lower() == name.lower():
                account_id = a["id"]
                account_balance = a["attributes"].get("current_balance", "0.00")
                break

        if not account_id:
            await query.message.reply_text("Cuenta no encontrada.")
            return

        tx_url = f"{FIREFLY_URL}/api/v1/accounts/{account_id}/transactions?limit=3"
        tx_response = requests.get(tx_url, headers=headers)
        tx_response.raise_for_status()
        transactions = tx_response.json().get("data", [])

        lines = [f"cuenta: {name}", f"balance: {float(account_balance):.2f}", "movimientos:"]
        for t in transactions:
            for split in t["attributes"].get("transactions", []):
                raw_date = split.get("date", "-")
                date_str = raw_date.split("T")[0] if "T" in raw_date else raw_date
                desc = split.get("description", "-")
                amt = float(split.get("amount", "0.00"))
                lines.append(f"{date_str} {desc} {amt:.2f}")

        await query.message.reply_text("\n".join(lines))

    except Exception as e:
        logging.error(f"Error en show_account_from_callback: {e}")
        await query.message.reply_text("Error al obtener los datos de la cuenta.")


if __name__ == '__main__':
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("assets", list_assets))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'^/expense\s'), create_expense))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'^/cuenta\s'), lambda u, c: show_account(u, c)))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.run_polling()
