"""Shared helpers for account display and common utilities."""
from typing import Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from bot.client import get_accounts, safe_get


async def format_account_display(
    account_name: str,
    limit: int = 3,
) -> Optional[str]:
    """Format account info and recent transactions as a text message.

    Returns formatted string or None if account not found.
    """
    accounts = get_accounts()
    account_id = None
    balance = "0.00"

    for a in accounts:
        if a["attributes"]["name"].lower() == account_name.lower():
            account_id = a["id"]
            balance = a["attributes"].get("current_balance", "0.00")
            break

    if not account_id:
        return None

    txs = safe_get(
        f"/api/v1/accounts/{account_id}/transactions",
        params={"limit": limit},
    )

    lines = [
        f"📊 *{account_name}*",
        f"💰 Balance: {float(balance):.2f}",
        f"📋 Últimos {limit} movimientos:",
        "---",
    ]

    for t in txs:
        for s in t["attributes"].get("transactions", []):
            fecha = s.get("date", "").split("T")[0]
            desc = s.get("description", "-")
            monto = float(s.get("amount", "0.00"))
            lines.append(f"{fecha} | {desc} | {monto:.2f}")

    return "\n".join(lines)


async def list_commands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    commands = [
        "/start - Muestra el menú principal",
        "/menu - Reabre el menú de opciones",
        "/assets - Lista tus cuentas de activo",
        "/cuenta <nombre> <N> - Muestra movimientos de una cuenta",
        "/gasto <monto> <desc> <origen> [cat] [dest] - Registro rápido de gasto",
        "/expenseButton - Registro de gasto paso a paso con botones",
        "/cancel - Cancela el flujo actual",
        "/refresh - Refresca el caché de cuentas/categorías",
    ]
    text = "📋 *Comandos disponibles:*\n" + "\n".join(commands)

    if update.message:
        await update.message.reply_text(text, parse_mode="Markdown")
    elif update.callback_query:
        await update.callback_query.message.reply_text(text, parse_mode="Markdown")
