from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from bot.client import get_accounts
from bot.config import FIREFLY_URL
import logging
import requests

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

    headers = {"Authorization": f"Bearer {context.bot_data['FIREFLY_TOKEN']}"} if 'FIREFLY_TOKEN' in context.bot_data else {}
    try:
        accounts = get_accounts()
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

account_handlers = [
    CommandHandler("cuenta", show_account)
]
