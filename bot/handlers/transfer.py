import logging
from datetime import datetime

import pytz
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from bot.client import create_transaction, get_accounts
from bot.config import OCULTAR_CUENTAS_LOWER, TIMEZONE
from bot.constants import (
    TRANSFER_CONFIRM,
    TRANSFER_ENTER_AMOUNT,
    TRANSFER_SELECT_DESTINATION,
    TRANSFER_SELECT_SOURCE,
)
from bot.middleware import require_auth, validate_amount

logger = logging.getLogger(__name__)


def _chunk_buttons(buttons: list[InlineKeyboardButton], columns: int = 2) -> list[list[InlineKeyboardButton]]:
    return [buttons[index:index + columns] for index in range(0, len(buttons), columns)]


def _get_keyboard_with_cancel(buttons: list[list[InlineKeyboardButton]]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        buttons + [[InlineKeyboardButton("❌ Cancelar", callback_data="cancel_transfer")]]
    )


def _get_visible_asset_accounts(accounts: list[dict]) -> list[dict]:
    visible_accounts = []
    for account in accounts:
        attributes = account.get("attributes", {})
        if attributes.get("type") != "asset":
            continue

        name = attributes.get("name", "")
        if not name or name.lower() in OCULTAR_CUENTAS_LOWER:
            continue

        visible_accounts.append(account)

    return visible_accounts


def _build_account_keyboard(accounts: list[dict], prefix: str) -> list[list[InlineKeyboardButton]]:
    buttons = [
        InlineKeyboardButton(
            account["attributes"]["name"],
            callback_data=f"{prefix}{account['id']}",
        )
        for account in accounts
    ]
    return _chunk_buttons(buttons)


def _find_account_by_id(accounts: list[dict], account_id: str):
    for account in accounts:
        if account.get("id") == account_id:
            return account
    return None


def _get_transfer_accounts() -> list[dict]:
    return _get_visible_asset_accounts(get_accounts(account_type="asset"))


def _build_confirmation_text(user_data: dict) -> str:
    return "\n".join(
        [
            "Resumen de la transferencia:",
            f"Monto: {user_data['amount']:.2f}",
            f"Origen: {user_data['source_name']}",
            f"Destino: {user_data['destination_name']}",
            f"Descripción: transferencia {user_data['source_name']}-{user_data['destination_name']}",
            "¿Confirmás la transferencia?",
        ]
    )


async def start_transfer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_auth(update, context):
        return ConversationHandler.END

    accounts = _get_transfer_accounts()
    if len(accounts) < 2:
        message_source = update.message or update.callback_query.message
        await message_source.reply_text(
            "No hay cuentas disponibles para registrar una transferencia."
        )
        return ConversationHandler.END

    context.user_data.clear()
    message_source = update.message or update.callback_query.message
    await message_source.reply_text("Ingresá el monto de la transferencia.")
    return TRANSFER_ENTER_AMOUNT


async def enter_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    amount = validate_amount(update.message.text.strip())
    if amount is None or amount <= 0:
        await update.message.reply_text("Monto inválido. Usá un número positivo.")
        return TRANSFER_ENTER_AMOUNT

    accounts = _get_transfer_accounts()
    if len(accounts) < 2:
        await update.message.reply_text(
            "No hay cuentas disponibles para continuar con la transferencia."
        )
        return ConversationHandler.END

    context.user_data["amount"] = amount
    keyboard = _build_account_keyboard(accounts, "transfer_source::")
    await update.message.reply_text(
        "Seleccioná la cuenta de origen:",
        reply_markup=_get_keyboard_with_cancel(keyboard),
    )
    return TRANSFER_SELECT_SOURCE


async def select_source(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    accounts = _get_transfer_accounts()
    source_id = query.data.replace("transfer_source::", "")
    source_account = _find_account_by_id(accounts, source_id)
    if not source_account:
        await query.message.reply_text("No se pudo identificar la cuenta de origen.")
        return ConversationHandler.END

    destination_accounts = [account for account in accounts if account.get("id") != source_id]
    if not destination_accounts:
        await query.message.reply_text(
            "No hay cuentas disponibles para seleccionar como destino."
        )
        return ConversationHandler.END

    context.user_data["source_id"] = source_account["id"]
    context.user_data["source_name"] = source_account["attributes"]["name"]
    keyboard = _build_account_keyboard(destination_accounts, "transfer_destination::")
    await query.message.reply_text(
        "Seleccioná la cuenta de destino:",
        reply_markup=_get_keyboard_with_cancel(keyboard),
    )
    return TRANSFER_SELECT_DESTINATION


async def select_destination(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    accounts = _get_transfer_accounts()
    destination_id = query.data.replace("transfer_destination::", "")

    if destination_id == context.user_data.get("source_id"):
        await query.message.reply_text(
            "La cuenta de destino tiene que ser distinta de la cuenta de origen."
        )
        return TRANSFER_SELECT_DESTINATION

    destination_account = _find_account_by_id(accounts, destination_id)
    if not destination_account:
        await query.message.reply_text("No se pudo identificar la cuenta de destino.")
        return ConversationHandler.END

    context.user_data["destination_id"] = destination_account["id"]
    context.user_data["destination_name"] = destination_account["attributes"]["name"]

    keyboard = [[
        InlineKeyboardButton("✅ Confirmar", callback_data="confirm_transfer"),
        InlineKeyboardButton("❌ Cancelar", callback_data="cancel_transfer"),
    ]]
    await query.message.reply_text(
        _build_confirmation_text(context.user_data),
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return TRANSFER_CONFIRM


async def confirm_transfer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_data = context.user_data
    payload = {
        "transactions": [
            {
                "type": "transfer",
                "amount": str(user_data["amount"]),
                "description": (
                    f"transferencia {user_data['source_name']}-{user_data['destination_name']}"
                ),
                "source_id": user_data["source_id"],
                "destination_id": user_data["destination_id"],
                "date": datetime.now(pytz.timezone(TIMEZONE)).isoformat(),
            }
        ]
    }

    response = None
    try:
        response = create_transaction(payload)
        response.raise_for_status()
        await query.message.reply_text("✅ Transferencia registrada correctamente.")
    except Exception as error:
        logger.error("Error creating transfer transaction: %s", error)
        error_detail = ""
        if response is not None:
            try:
                error_detail = response.json().get("message", "")
            except Exception:
                error_detail = ""
        await query.message.reply_text(
            f"❌ Error al registrar la transferencia.\nDetalles: {error_detail or str(error)}"
        )

    context.user_data.clear()
    return ConversationHandler.END


async def cancel_transfer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        await update.message.reply_text("❌ Transferencia cancelada. No se ejecutó la operación.")
    elif update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.reply_text(
            "❌ Transferencia cancelada. No se ejecutó la operación."
        )

    context.user_data.clear()
    return ConversationHandler.END


transfer_conv = ConversationHandler(
    entry_points=[
        CommandHandler("transferencia", start_transfer),
        CallbackQueryHandler(start_transfer, pattern="^menu_transfer$"),
    ],
    states={
        TRANSFER_ENTER_AMOUNT: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, enter_amount),
        ],
        TRANSFER_SELECT_SOURCE: [
            CallbackQueryHandler(select_source, pattern="^transfer_source::"),
        ],
        TRANSFER_SELECT_DESTINATION: [
            CallbackQueryHandler(select_destination, pattern="^transfer_destination::"),
        ],
        TRANSFER_CONFIRM: [
            CallbackQueryHandler(confirm_transfer, pattern="^confirm_transfer$"),
        ],
    },
    fallbacks=[
        CommandHandler("cancel", cancel_transfer),
        CallbackQueryHandler(cancel_transfer, pattern="^cancel_transfer$"),
    ],
    per_chat=True,
    per_message=False,
)


transfer_handlers = [transfer_conv]
