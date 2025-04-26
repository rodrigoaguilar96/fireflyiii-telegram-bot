import logging
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes, CallbackQueryHandler
from bot.client import get_accounts, safe_get
from bot.config import FIREFLY_URL
from bot.handlers.menu import handle_menu_selection


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

        txs = safe_get(f"/api/v1/accounts/{account_id}/transactions", params={"limit": n})

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

async def show_account_from_callback(query, context, name):
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
            await query.message.reply_text("Cuenta no encontrada.")
            return

        txs = safe_get(f"/api/v1/accounts/{account_id}/transactions", params={"limit": 3})

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

    # 🔒 Ignorar eventos reservados para el flujo de expense
    if data.startswith("origin::") or data.startswith("dest::") or data.startswith("cancelar"):
        logging.warning(f"🔁 Ignorando callback reservado para ConversationHandler: {data}")
        return

    logging.warning(f"📦 handle_callback captó: {data}")

    if data.startswith("cuenta::"):
        cuenta_name = data.replace("cuenta::", "")
        await show_account_from_callback(query, context, cuenta_name)
    elif data.startswith("menu_"):
        await handle_menu_selection(update, context)


account_handlers = [
    CommandHandler("cuenta", show_account),
    CallbackQueryHandler(handle_callback, pattern="^cuenta::")
]
