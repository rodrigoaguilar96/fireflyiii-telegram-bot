import logging
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation

import pytz
from telegram import Update
from telegram.ext import ContextTypes

from bot import client
from bot.config import TIMEZONE


EMPTY_SUBSCRIPTIONS_MESSAGE = "✅ No tenés suscripciones pendientes en el período actual."
SUBSCRIPTIONS_ERROR_MESSAGE = "No se pudieron obtener las suscripciones pendientes ahora."


def get_current_period_bounds() -> tuple[str, str]:
    """Return current local month boundaries as Firefly YYYY-MM-DD strings."""
    timezone = pytz.timezone(TIMEZONE)
    today = datetime.now(timezone).date()
    start = today.replace(day=1)
    if start.month == 12:
        next_month = start.replace(year=start.year + 1, month=1)
    else:
        next_month = start.replace(month=start.month + 1)
    end = next_month - timedelta(days=1)
    return start.isoformat(), end.isoformat()


def _normalize_date(value) -> str | None:
    if isinstance(value, dict):
        value = value.get("date")
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip()[:10]


def _normalized_dates(values) -> set[str]:
    if not isinstance(values, list):
        return set()
    return {date for date in (_normalize_date(value) for value in values) if date}


def _format_amount(attributes: dict) -> str:
    amount_min = attributes.get("amount_min")
    amount_max = attributes.get("amount_max")
    currency = attributes.get("currency_symbol") or attributes.get("currency_code") or ""
    suffix = f" {currency}" if currency else ""

    if not amount_min or _parse_amount(amount_min) is None:
        return "monto no disponible"
    if amount_max and amount_max != amount_min and _parse_amount(amount_max) is not None:
        return f"{amount_min} - {amount_max}{suffix}"
    return f"{amount_min}{suffix}"


def _parse_amount(value: str) -> Decimal | None:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def extract_pending_subscriptions(bills: list, start: str, end: str) -> list[dict]:
    """Extract unpaid subscription due instances inside inclusive period bounds."""
    pending = []
    for bill in bills:
        if not isinstance(bill, dict):
            continue
        attributes = bill.get("attributes")
        if not isinstance(attributes, dict):
            continue
        name = attributes.get("name")
        if attributes.get("active") is not True or not name:
            continue

        paid_dates = _normalized_dates(attributes.get("paid_dates", []))
        for due_date in sorted(_normalized_dates(attributes.get("pay_dates", []))):
            if start <= due_date <= end and due_date not in paid_dates:
                pending.append(
                    {
                        "name": name,
                        "due_date": due_date,
                        "amount": _format_amount(attributes),
                    }
                )
    return sorted(pending, key=lambda item: (item["due_date"], item["name"]))


def build_pending_subscriptions_message(bills: list, start: str, end: str) -> str:
    pending = extract_pending_subscriptions(bills, start, end)
    if not pending:
        return EMPTY_SUBSCRIPTIONS_MESSAGE

    lines = ["Suscripciones pendientes del período actual:"]
    lines.extend(
        f"• {item['name']} — vence {item['due_date']} — {item['amount']}"
        for item in pending
    )
    return "\n".join(lines)


async def show_current_period_subscriptions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        start, end = get_current_period_bounds()
        bills = client.get_bills_for_period(start, end)
        message = build_pending_subscriptions_message(bills, start, end)
    except Exception:
        logging.exception("Error obteniendo suscripciones pendientes")
        message = SUBSCRIPTIONS_ERROR_MESSAGE

    target = update.callback_query.message if update.callback_query else update.message
    await target.reply_text(message)
