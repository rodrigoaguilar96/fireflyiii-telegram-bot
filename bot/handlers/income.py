"""Income flow handlers — destination, amount/description, confirmation."""
import logging
from datetime import datetime
from typing import Optional

import pytz
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from bot.client import create_transaction, get_accounts
from bot.config import OCULTAR_CUENTAS_LOWER, TIMEZONE
from bot.constants import (
    EXPENSE_BUTTON_PATTERN,
    INCOME_CONFIRM,
    INCOME_ENTER_AMOUNT_DESC,
    INCOME_SELECT_DESTINATION,
    MENU_BUTTON_PATTERN,
)
from bot.handlers.common import cancel_current_flow_for_expense_shortcut
from bot.handlers.menu import cancel_to_menu
from bot.middleware import require_auth, sanitize_text, validate_amount

logger = logging.getLogger(__name__)

MAX_DESCRIPTION_LENGTH = 255


def _get_keyboard_with_cancel(buttons: list[list]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        buttons + [[InlineKeyboardButton("❌ Cancelar", callback_data="cancelar_ingreso")]]
    )


def _chunk_buttons(buttons: list[InlineKeyboardButton], columns: int = 2) -> list[list]:
    return [buttons[i : i + columns] for i in range(0, len(buttons), columns)]


def _find_account_by_name(accounts: list, name: str) -> Optional[dict]:
    name_lower = name.lower()
    for account in accounts:
        if account["attributes"]["name"].lower() == name_lower:
            return account
    return None


def _build_confirmation_summary(context: dict) -> str:
    return "\n".join(
        [
            "📝 *Resumen del ingreso:*",
            "---",
            f"💰 Monto: {context['amount']:.2f}",
            f"📄 Descripción: {context['description']}",
            f"🏦 Cuenta destino: {context['destination']}",
            "---",
            "¿Confirmás el ingreso?",
        ]
    )


async def start_income_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Entry point for the step-by-step income flow."""
    if not await require_auth(update, context):
        return ConversationHandler.END

    logger.info("Starting income button flow")
    context.user_data.clear()

    account_buttons = []
    for account in get_accounts(account_type="asset"):
        name = account["attributes"]["name"]
        if name.lower() in OCULTAR_CUENTAS_LOWER:
            continue
        account_buttons.append(
            InlineKeyboardButton(name, callback_data=f"income_dest::{name.lower()}")
        )

    msg_source = update.message or update.callback_query.message
    await msg_source.reply_text(
        "Seleccioná la cuenta destino:",
        reply_markup=_get_keyboard_with_cancel(_chunk_buttons(account_buttons)),
    )
    return INCOME_SELECT_DESTINATION


async def select_income_destination(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle destination asset account selection."""
    query = update.callback_query
    await query.answer()

    destination = query.data.replace("income_dest::", "", 1)
    context.user_data["destination"] = destination
    logger.info("Income destination selected: %s", destination)

    await query.message.reply_text(
        "Ahora escribí el monto y la descripción.\n"
        "Ejemplo: `1500 sueldo`",
        reply_markup=_get_keyboard_with_cancel([]),
    )
    return INCOME_ENTER_AMOUNT_DESC


async def enter_income_amount_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Parse income amount and description from user input."""
    text = update.message.text.strip()

    amount = validate_amount(text.split()[0] if text else "")
    if amount is None or amount <= 0:
        await update.message.reply_text(
            "Monto inválido. Usá un número positivo.\n"
            "Ejemplo: `1500 sueldo`"
        )
        return INCOME_ENTER_AMOUNT_DESC

    parts = text.split(None, 1)
    description = sanitize_text(parts[1], MAX_DESCRIPTION_LENGTH) if len(parts) > 1 else ""
    if not description:
        await update.message.reply_text(
            "Falta la descripción. Escribí el monto y la descripción juntos.\n"
            "Ejemplo: `1500 sueldo`"
        )
        return INCOME_ENTER_AMOUNT_DESC

    context.user_data["amount"] = amount
    context.user_data["description"] = description
    return await _show_income_confirmation(update.message, context)


async def _show_income_confirmation(message_source, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("✅ Confirmar", callback_data="confirm_income"),
            InlineKeyboardButton("❌ Cancelar", callback_data="cancelar_ingreso"),
        ]
    ]
    await message_source.reply_text(
        _build_confirmation_summary(context.user_data),
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return INCOME_CONFIRM


async def confirm_income(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle income confirmation and create transaction."""
    query = update.callback_query
    await query.answer()

    if query.data != "confirm_income":
        return ConversationHandler.END

    await _create_income_transaction(query.message, context)
    return ConversationHandler.END


async def _create_income_transaction(message_source, context: ContextTypes.DEFAULT_TYPE):
    """Create the income transaction in Firefly III."""
    user_data = context.user_data
    accounts = get_accounts(account_type="asset")
    destination_account = _find_account_by_name(accounts, user_data.get("destination", ""))
    if not destination_account:
        await message_source.reply_text("❌ Cuenta destino no encontrada.")
        return

    transaction = {
        "type": "deposit",
        "amount": format(user_data["amount"], ".2f"),
        "description": user_data["description"],
        "destination_id": destination_account["id"],
        "date": datetime.now(pytz.timezone(TIMEZONE)).isoformat(),
    }
    payload = {"transactions": [transaction]}

    logger.info("Creating income transaction for destination account id=%s", destination_account["id"])
    response = None
    try:
        response = create_transaction(payload)
        response.raise_for_status()
        await message_source.reply_text(
            f"✅ Ingreso registrado correctamente:\n"
            f"💰 {user_data['amount']:.2f} — {user_data['description']}"
        )
    except Exception as exc:
        logger.error("Error creating income transaction: %s", exc)
        error_detail = ""
        if response is not None:
            try:
                error_detail = response.json().get("message", "")
            except Exception:
                pass
        await message_source.reply_text(
            f"❌ Error al registrar el ingreso.\n"
            f"Detalles: {error_detail or str(exc)}"
        )


async def cancel_income(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel the current income conversation and clear user data."""
    logger.info("Canceling income flow")
    if update.message:
        await update.message.reply_text("❌ Operación cancelada.")
    elif update.callback_query:
        await update.callback_query.message.reply_text("❌ Operación cancelada.")
    context.user_data.clear()
    return ConversationHandler.END


income_conv = ConversationHandler(
    entry_points=[CallbackQueryHandler(start_income_button, pattern="^menu_income$")],
    states={
        INCOME_SELECT_DESTINATION: [
            MessageHandler(filters.Regex(MENU_BUTTON_PATTERN), cancel_to_menu),
            MessageHandler(
                filters.Regex(EXPENSE_BUTTON_PATTERN),
                cancel_current_flow_for_expense_shortcut,
            ),
            CallbackQueryHandler(select_income_destination, pattern="^income_dest::"),
        ],
        INCOME_ENTER_AMOUNT_DESC: [
            MessageHandler(filters.Regex(MENU_BUTTON_PATTERN), cancel_to_menu),
            MessageHandler(
                filters.Regex(EXPENSE_BUTTON_PATTERN),
                cancel_current_flow_for_expense_shortcut,
            ),
            MessageHandler(filters.TEXT & ~filters.COMMAND, enter_income_amount_description),
        ],
        INCOME_CONFIRM: [
            MessageHandler(filters.Regex(MENU_BUTTON_PATTERN), cancel_to_menu),
            MessageHandler(
                filters.Regex(EXPENSE_BUTTON_PATTERN),
                cancel_current_flow_for_expense_shortcut,
            ),
            CallbackQueryHandler(confirm_income, pattern="^confirm_income$"),
        ],
    },
    fallbacks=[
        CommandHandler("cancel", cancel_income),
        CommandHandler("start", cancel_to_menu),
        CommandHandler("menu", cancel_to_menu),
        CommandHandler(
            "expenseButton",
            cancel_current_flow_for_expense_shortcut,
        ),
        MessageHandler(filters.Regex(MENU_BUTTON_PATTERN), cancel_to_menu),
        MessageHandler(
            filters.Regex(EXPENSE_BUTTON_PATTERN),
            cancel_current_flow_for_expense_shortcut,
        ),
        CallbackQueryHandler(cancel_income, pattern="^cancelar_ingreso$"),
    ],
    per_chat=True,
    per_message=False,
)

income_handlers = [income_conv]
