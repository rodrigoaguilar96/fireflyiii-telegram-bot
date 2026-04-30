"""Expense flow handlers — step-by-step button flow and quick command."""
import logging
from datetime import datetime
from typing import Optional

import pytz
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from bot.client import (
    get_accounts,
    get_bills,
    get_categories,
    get_budgets,
    create_transaction,
    create_account,
    refresh_cache,
)
from bot.config import OCULTAR_CUENTAS_LOWER, TIMEZONE
from bot.constants import (
    SELECT_ORIGIN,
    ENTER_AMOUNT_DESC,
    SELECT_DESTINATION,
    ENTER_NEW_DEST_NAME,
    SELECT_CATEGORY,
    SELECT_BUDGET,
    SELECT_BILL,
    ENTER_TAGS,
    CONFIRM_EXPENSE,
)
from bot.middleware import require_auth, validate_amount, sanitize_text
from bot.handlers.common import list_commands

logger = logging.getLogger(__name__)

# ─── Helpers ───────────────────────────────────────────────

MAX_RECENT_DESTINATIONS = 10
MAX_DESCRIPTION_LENGTH = 255
MAX_TAG_LENGTH = 50


def _get_keyboard_with_cancel(buttons: list[list]) -> InlineKeyboardMarkup:
    """Wrap button rows with a cancel button at the bottom."""
    return InlineKeyboardMarkup(
        buttons + [[InlineKeyboardButton("❌ Cancelar", callback_data="cancelar")]]
    )


def _get_recent_destinations(context: ContextTypes.DEFAULT_TYPE) -> list[str]:
    """Get list of recent destination names from user_data."""
    return context.user_data.get("recent_destinations", [])


def _chunk_buttons(buttons: list[InlineKeyboardButton], columns: int = 2) -> list[list]:
    """Group buttons into rows with the requested number of columns."""
    return [buttons[i : i + columns] for i in range(0, len(buttons), columns)]


def _add_recent_destination(context: ContextTypes.DEFAULT_TYPE, name: str) -> None:
    """Add a destination to the recent list (most recent first, deduplicated)."""
    recent = context.user_data.get("recent_destinations", [])
    # Remove if already present (to re-add at top)
    recent = [d for d in recent if d.lower() != name.lower()]
    recent.insert(0, name)
    context.user_data["recent_destinations"] = recent[:MAX_RECENT_DESTINATIONS]


def _find_account_by_name(accounts: list, name: str) -> Optional[dict]:
    """Find an account by name (case-insensitive)."""
    name_lower = name.lower()
    for a in accounts:
        if a["attributes"]["name"].lower() == name_lower:
            return a
    return None


def _build_destination_keyboard(
    accounts: list, context: ContextTypes.DEFAULT_TYPE
) -> list[list]:
    """Build destination keyboard with recent destinations first."""
    recent = _get_recent_destinations(context)
    keyboard = []

    # Recent destinations section
    if recent:
        recent_names_lower = [r.lower() for r in recent]
        recent_accounts = [
            a for a in accounts if a["attributes"]["name"].lower() in recent_names_lower
        ]
        # Sort by recency
        recent_accounts.sort(
            key=lambda a: recent_names_lower.index(a["attributes"]["name"].lower())
        )

        if recent_accounts:
            keyboard.append(
                [InlineKeyboardButton("🕐 Recientes", callback_data="__separator__")]
            )
            recent_buttons = []
            for a in recent_accounts:
                name = a["attributes"]["name"]
                recent_buttons.append(
                    InlineKeyboardButton(
                        f"🕐 {name}", callback_data=f"dest::{name.lower()}"
                    )
                )
            keyboard.extend(_chunk_buttons(recent_buttons))
            keyboard.append(
                [InlineKeyboardButton("── Todas las cuentas ──", callback_data="__separator__")]
            )

    # All other destinations
    recent_names_lower = [r.lower() for r in recent]
    destination_buttons = []
    for a in accounts:
        name = a["attributes"]["name"]
        if name.lower() in recent_names_lower:
            continue  # Already shown in recent section
        destination_buttons.append(
            InlineKeyboardButton(name, callback_data=f"dest::{name.lower()}")
        )
    keyboard.extend(_chunk_buttons(destination_buttons))

    # Skip option
    keyboard.append(
        [InlineKeyboardButton("⏭️ Sin cuenta destino", callback_data="dest::none")]
    )
    keyboard.append(
        [InlineKeyboardButton("➕ Crear nueva cuenta", callback_data="dest::new")]
    )

    return keyboard


def _build_category_keyboard(categories: list) -> list[list]:
    """Build category selection keyboard (2 per row)."""
    keyboard = []
    row = []
    for cat in categories[:20]:  # Limit to 20 to avoid Telegram button limit
        name = cat["attributes"]["name"]
        row.append(InlineKeyboardButton(name, callback_data=f"cat::{name}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    # Skip option
    keyboard.append(
        [InlineKeyboardButton("⏭️ Sin categoría", callback_data="cat::none")]
    )
    return keyboard


def _build_budget_keyboard(budgets: list) -> list[list]:
    """Build budget selection keyboard."""
    keyboard = []
    for b in budgets[:15]:
        name = b["attributes"]["name"]
        keyboard.append(
            [InlineKeyboardButton(name, callback_data=f"budget::{name}")]
        )

    # Skip option
    keyboard.append(
        [InlineKeyboardButton("⏭️ Sin presupuesto", callback_data="budget::none")]
    )
    return keyboard


def _get_usable_active_bills(bills: list) -> list[dict]:
    """Keep only active bills with usable identifier and name."""
    usable_bills = []
    for bill in bills:
        if not isinstance(bill, dict):
            continue

        bill_id = bill.get("id")
        attributes = bill.get("attributes")
        if not bill_id or not isinstance(attributes, dict):
            continue

        name = attributes.get("name")
        if not isinstance(name, str) or not name.strip():
            continue

        if attributes.get("active") is not True:
            continue

        usable_bills.append(
            {
                "id": str(bill_id),
                "attributes": {"name": name.strip(), "active": True},
            }
        )

    return usable_bills


def _build_bill_keyboard(bills: list[dict]) -> list[list]:
    """Build bill selection keyboard using existing multi-column style."""
    bill_buttons = [
        InlineKeyboardButton(
            bill["attributes"]["name"], callback_data=f"bill::{bill['id']}"
        )
        for bill in bills[:20]
    ]
    keyboard = _chunk_buttons(bill_buttons, 2)
    keyboard.append(
        [
            InlineKeyboardButton(
                "⏭️ Sin suscripción/factura", callback_data="bill::none"
            )
        ]
    )
    return keyboard


def _build_confirmation_summary(context: dict) -> str:
    """Build a human-readable summary of the expense for confirmation."""
    lines = [
        "📝 *Resumen del gasto:*",
        "---",
        f"💰 Monto: {context['amount']:.2f}",
        f"📄 Descripción: {context['description']}",
        f"🏦 Origen: {context['origin']}",
    ]

    dest = context.get("destination")
    if dest and dest != "none":
        lines.append(f"🎯 Destino: {dest}")
    else:
        lines.append("🎯 Destino: _Sin cuenta destino_")

    cat = context.get("category")
    if cat and cat != "none":
        lines.append(f"📂 Categoría: {cat}")
    else:
        lines.append("📂 Categoría: _Sin categoría_")

    budget = context.get("budget")
    if budget and budget != "none":
        lines.append(f"📊 Presupuesto: {budget}")
    else:
        lines.append("📊 Presupuesto: _Sin presupuesto_")

    bill_name = context.get("bill_name")
    if bill_name:
        lines.append(f"🧾 Suscripción/Factura: {bill_name}")

    tags = context.get("tags", [])
    if tags:
        lines.append(f"🏷️ Tags: {', '.join(tags)}")

    lines.append("---")
    lines.append("¿Confirmás el gasto?")

    return "\n".join(lines)


# ─── Conversation Steps ────────────────────────────────────

async def start_expense_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Entry point for the step-by-step expense flow."""
    if not await require_auth(update, context):
        return ConversationHandler.END

    logger.info("Starting expense button flow")

    # Clear any stale data from previous attempts
    context.user_data.clear()

    accounts = get_accounts(account_type="asset")
    account_buttons = []
    for a in accounts:
        name = a["attributes"]["name"]
        if name.lower() in OCULTAR_CUENTAS_LOWER:
            continue
        account_buttons.append(
            InlineKeyboardButton(name, callback_data=f"origin::{name.lower()}")
        )

    # Remember last used origin
    last_origin = context.user_data.get("last_origin")
    if last_origin:
        account_buttons.insert(
            0,
            InlineKeyboardButton(
                f"🕐 Última: {last_origin}",
                callback_data=f"origin::{last_origin.lower()}"
            ),
        )

    keyboard = _chunk_buttons(account_buttons)
    reply_markup = _get_keyboard_with_cancel(keyboard)

    msg_source = update.message or update.callback_query.message
    await msg_source.reply_text(
        "Seleccioná la cuenta de origen:", reply_markup=reply_markup
    )
    return SELECT_ORIGIN


async def select_origin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle origin account selection."""
    query = update.callback_query
    await query.answer()

    origin = query.data.replace("origin::", "")
    context.user_data["origin"] = origin
    context.user_data["last_origin"] = origin  # Remember for next time

    logger.info(f"Origin selected: {origin}")

    await query.message.reply_text(
        "Ahora escribí el monto y la descripción.\n"
        "Ejemplo: `13.99 hamburguesa`",
        reply_markup=_get_keyboard_with_cancel([]),
    )
    return ENTER_AMOUNT_DESC


async def enter_amount_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Parse amount and description from user input."""
    text = update.message.text.strip()

    amount = validate_amount(text.split()[0] if text else "")
    if amount is None or amount <= 0:
        await update.message.reply_text(
            "Monto inválido. Usá un número positivo.\n"
            "Ejemplo: `13.99 hamburguesa`"
        )
        return ENTER_AMOUNT_DESC

    # Extract description (everything after the amount)
    parts = text.split(None, 1)
    description = sanitize_text(parts[1], MAX_DESCRIPTION_LENGTH) if len(parts) > 1 else ""

    if not description:
        await update.message.reply_text(
            "Falta la descripción. Escribí el monto y la descripción juntos.\n"
            "Ejemplo: `13.99 hamburguesa`"
        )
        return ENTER_AMOUNT_DESC

    context.user_data["amount"] = amount
    context.user_data["description"] = description

    # Show destination selection
    accounts = get_accounts(account_type="expense")
    keyboard = _build_destination_keyboard(accounts, context)

    reply_markup = _get_keyboard_with_cancel(keyboard)
    await update.message.reply_text(
        "Seleccioná la cuenta de destino:",
        reply_markup=reply_markup,
    )
    return SELECT_DESTINATION


async def select_destination(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle destination account selection."""
    query = update.callback_query
    await query.answer()

    dest = query.data.replace("dest::", "")

    if dest == "new":
        await query.message.reply_text(
            "Escribí el nombre de la nueva cuenta de destino:",
            reply_markup=_get_keyboard_with_cancel([]),
        )
        return ENTER_NEW_DEST_NAME

    if dest == "none":
        context.user_data["destination"] = None
        logger.info("No destination selected")
    else:
        context.user_data["destination"] = dest
        _add_recent_destination(context, dest)
        logger.info(f"Destination selected: {dest}")

    # Move to category selection
    return await _show_category_selection(query.message, context)


async def enter_new_dest_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Create a new destination account."""
    new_name = sanitize_text(update.message.text.strip())

    if not new_name:
        await update.message.reply_text(
            "El nombre no puede estar vacío. Escribí un nombre válido:"
        )
        return ENTER_NEW_DEST_NAME

    try:
        result = create_account(new_name)
        result.raise_for_status()
        dest_name = result.json().get("data", {}).get("attributes", {}).get("name", new_name)
        context.user_data["destination"] = dest_name
        _add_recent_destination(context, dest_name)
        logger.info(f"Created new destination account: {dest_name}")
    except Exception as e:
        logger.error(f"Error creating new account: {e}")
        await update.message.reply_text(
            "No se pudo crear la nueva cuenta. Intentá de nuevo o elegí otra."
        )
        return ENTER_NEW_DEST_NAME

    return await _show_category_selection(update.message, context)


async def _show_category_selection(message_source, context: ContextTypes.DEFAULT_TYPE):
    """Show category selection keyboard."""
    categories = get_categories()

    if not categories:
        logger.warning("No categories found, skipping category selection")
        context.user_data["category"] = None
        return await _show_budget_selection(message_source, context)

    keyboard = _build_category_keyboard(categories)
    reply_markup = _get_keyboard_with_cancel(keyboard)

    await message_source.reply_text(
        "Seleccioná una categoría:",
        reply_markup=reply_markup,
    )
    return SELECT_CATEGORY


async def select_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle category selection."""
    query = update.callback_query
    await query.answer()

    category = query.data.replace("cat::", "")

    if category == "none":
        context.user_data["category"] = None
        logger.info("No category selected")
    else:
        context.user_data["category"] = category
        logger.info(f"Category selected: {category}")

    return await _show_budget_selection(query.message, context)


async def _show_budget_selection(message_source, context: ContextTypes.DEFAULT_TYPE):
    """Show budget selection keyboard."""
    budgets = get_budgets()

    if not budgets:
        logger.debug("No budgets found, skipping budget selection")
        context.user_data["budget"] = None
        return await _show_bill_selection(message_source, context)

    keyboard = _build_budget_keyboard(budgets)
    reply_markup = _get_keyboard_with_cancel(keyboard)

    await message_source.reply_text(
        "Seleccioná un presupuesto (opcional):",
        reply_markup=reply_markup,
    )
    return SELECT_BUDGET


async def select_budget(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle budget selection."""
    query = update.callback_query
    await query.answer()

    budget = query.data.replace("budget::", "")

    if budget == "none":
        context.user_data["budget"] = None
        context.user_data.pop("budget_id", None)
        logger.info("No budget selected")
    else:
        context.user_data["budget"] = budget
        context.user_data["budget_id"] = query.data  # Store full data for ID lookup
        logger.info(f"Budget selected: {budget}")

    return await _show_bill_selection(query.message, context)


async def _show_bill_selection(message_source, context: ContextTypes.DEFAULT_TYPE):
    """Show bill selection keyboard or fall through to tags on unusable data."""
    bills = get_bills()
    usable_bills = _get_usable_active_bills(bills)

    if not usable_bills:
        logger.info("No usable active bills found, skipping bill selection")
        context.user_data.pop("bill_id", None)
        context.user_data.pop("bill_name", None)
        return await _show_tag_input(message_source, context)

    keyboard = _build_bill_keyboard(usable_bills)
    reply_markup = _get_keyboard_with_cancel(keyboard)

    await message_source.reply_text(
        "Seleccioná una suscripción o factura (opcional):",
        reply_markup=reply_markup,
    )
    return SELECT_BILL


async def select_bill(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle bill selection or skip action."""
    query = update.callback_query
    await query.answer()

    bill_value = query.data.replace("bill::", "", 1)

    if bill_value == "none":
        context.user_data.pop("bill_id", None)
        context.user_data.pop("bill_name", None)
        logger.info("No bill selected")
        return await _show_tag_input(query.message, context)

    usable_bills = _get_usable_active_bills(get_bills())
    selected_bill = next((bill for bill in usable_bills if bill["id"] == bill_value), None)
    if not selected_bill:
        logger.warning("Selected bill not found in usable active bill list: %s", bill_value)
        context.user_data.pop("bill_id", None)
        context.user_data.pop("bill_name", None)
        return await _show_tag_input(query.message, context)

    context.user_data["bill_id"] = selected_bill["id"]
    context.user_data["bill_name"] = selected_bill["attributes"]["name"]
    logger.info("Bill selected: %s (%s)", selected_bill["attributes"]["name"], selected_bill["id"])
    return await _show_tag_input(query.message, context)


async def _show_tag_input(message_source, context: ContextTypes.DEFAULT_TYPE):
    """Prompt for tags input."""
    await message_source.reply_text(
        "Escribí tags separados por coma (opcional).\n"
        "Ejemplo: `comida, delivery, almuerzo`\n\n"
        "O tocá el botón para continuar sin tags.",
        reply_markup=_get_keyboard_with_cancel(
            [[InlineKeyboardButton("⏭️ Sin tags", callback_data="tags::none")]]
        ),
    )
    return ENTER_TAGS


async def skip_tags(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Skip tags from the inline button."""
    query = update.callback_query
    await query.answer()

    context.user_data["tags"] = []
    logger.info("No tags entered")

    return await _show_confirmation(query.message, context)


async def enter_tags(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Parse and store tags."""
    text = update.message.text.strip()

    if text.lower() in ("skip", "no", "ninguno", ""):
        context.user_data["tags"] = []
        logger.info("No tags entered")
    else:
        tags = [
            sanitize_text(t.strip(), MAX_TAG_LENGTH)
            for t in text.split(",")
            if t.strip()
        ]
        context.user_data["tags"] = tags
        logger.info(f"Tags entered: {tags}")

    # Show confirmation
    return await _show_confirmation(update.message, context)


async def _show_confirmation(message_source, context: ContextTypes.DEFAULT_TYPE):
    """Show expense summary for confirmation."""
    summary = _build_confirmation_summary(context.user_data)

    keyboard = [
        [
            InlineKeyboardButton("✅ Confirmar", callback_data="confirm_expense"),
            InlineKeyboardButton("❌ Cancelar", callback_data="cancelar"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await message_source.reply_text(
        summary,
        reply_markup=reply_markup,
        parse_mode="Markdown",
    )
    return CONFIRM_EXPENSE


async def confirm_expense(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle expense confirmation and create transaction."""
    query = update.callback_query
    await query.answer()

    if query.data != "confirm_expense":
        return ConversationHandler.END

    await _create_expense_transaction(query.message, context)
    return ConversationHandler.END


async def _create_expense_transaction(message_source, context: ContextTypes.DEFAULT_TYPE):
    """Create the expense transaction in Firefly III."""
    ud = context.user_data
    accounts = get_accounts()

    # Find source account
    source_account = _find_account_by_name(accounts, ud.get("origin", ""))
    if not source_account:
        await message_source.reply_text("❌ Cuenta de origen no encontrada.")
        return

    source_id = source_account["id"]

    # Find destination account (if specified)
    destination_id = None
    dest_name = ud.get("destination")
    if dest_name:
        dest_account = _find_account_by_name(accounts, dest_name)
        if dest_account:
            destination_id = dest_account["id"]
        else:
            logger.warning(f"Destination account not found: {dest_name}")

    # Find category ID (if specified)
    category_name = ud.get("category")
    categories = get_categories()
    category_id = None
    if category_name:
        for cat in categories:
            if cat["attributes"]["name"].lower() == category_name.lower():
                category_id = cat["id"]
                break

    # Find budget ID (if specified)
    budget_id = None
    if ud.get("budget"):
        budgets = get_budgets()
        for b in budgets:
            if b["attributes"]["name"].lower() == ud["budget"].lower():
                budget_id = b["id"]
                break

    # Build transaction payload
    today = datetime.now(pytz.timezone(TIMEZONE)).isoformat()
    transaction = {
        "type": "withdrawal",
        "amount": str(ud["amount"]),
        "description": ud["description"],
        "source_id": source_id,
        "date": today,
    }

    if destination_id:
        transaction["destination_id"] = destination_id

    if category_id:
        transaction["category_id"] = category_id
    elif category_name:
        transaction["category_name"] = category_name  # Auto-creates if needed

    if budget_id:
        transaction["budget_id"] = budget_id

    bill_id = ud.get("bill_id")
    if bill_id:
        transaction["bill_id"] = bill_id

    tags = ud.get("tags", [])
    if tags:
        transaction["tags"] = tags

    payload = {"transactions": [transaction]}

    logger.info(f"Creating transaction: {payload}")

    response = None
    try:
        response = create_transaction(payload)
        response.raise_for_status()
        await message_source.reply_text(
            f"✅ Gasto registrado correctamente:\n"
            f"💰 {ud['amount']:.2f} — {ud['description']}"
        )
    except Exception as e:
        logger.error(f"Error creating transaction: {e}")
        error_detail = ""
        if response is not None:
            try:
                error_detail = response.json().get("message", "")
            except Exception:
                pass
        await message_source.reply_text(
            f"❌ Error al registrar el gasto.\n"
            f"Detalles: {error_detail or str(e)}"
        )


# ─── Quick Expense Command ─────────────────────────────────

USAGE_TEXT = (
    "💸 *Registrar gasto rápido*\n\n"
    "Uso:\n"
    "`/gasto <monto> <descripción> <origen> [categoría] [destino]`\n\n"
    "Ejemplos:\n"
    "`/gasto 20 burgerking tarjeta comida`\n"
    "`/gasto 13.99 uber transporte tarjeta credito`\n"
    "`/gasto 5.50 cafe efectivo`\n\n"
    "Notas:\n"
    "• `<origen>` es obligatorio — debe ser una cuenta existente\n"
    "• `[categoría]` es opcional — si no existe, se omite\n"
    "• `[destino]` es opcional — si no existe, se omite\n"
    "• Los nombres de cuentas y categorías no distinguen mayúsculas"
)


async def quick_expense(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Quick expense: /gasto <monto> <desc> <origen> [categoria] [destino]"""
    if not await require_auth(update, context):
        return

    args = context.args

    # Sin argumentos → mostrar instrucciones de uso
    if not args:
        await update.message.reply_text(USAGE_TEXT, parse_mode="Markdown")
        return

    # Mínimo: monto + descripción + origen
    if len(args) < 3:
        await update.message.reply_text(
            "❌ Faltan argumentos. Uso:\n"
            "`/gasto <monto> <descripción> <origen> [categoría] [destino]`\n\n"
            "Ejemplo: `/gasto 20 burgerking tarjeta comida`",
            parse_mode="Markdown",
        )
        return

    amount = validate_amount(args[0])
    if amount is None or amount <= 0:
        await update.message.reply_text("❌ Monto inválido. Usá un número positivo.")
        return

    description = sanitize_text(args[1], MAX_DESCRIPTION_LENGTH)
    origin = args[2].lower()
    category = sanitize_text(args[3]) if len(args) > 3 else None
    destination = args[4].lower() if len(args) > 4 else None

    # Buscar cuenta de origen (obligatoria)
    accounts = get_accounts()
    source_account = _find_account_by_name(accounts, origin)
    if not source_account:
        await update.message.reply_text(
            f"❌ Cuenta de origen '{origin}' no encontrada.\n"
            f"Usá /assets para ver tus cuentas disponibles."
        )
        return

    # Buscar categoría (opcional — si no existe, se omite)
    category_id = None
    category_applied = False
    if category:
        categories = get_categories()
        for cat in categories:
            if cat["attributes"]["name"].lower() == category.lower():
                category_id = cat["id"]
                category_applied = True
                break
        if not category_applied:
            logger.info(f"Category '{category}' not found, skipping")

    # Buscar destino (opcional — si no existe, se omite)
    destination_id = None
    destination_applied = False
    if destination:
        dest_account = _find_account_by_name(accounts, destination)
        if dest_account:
            destination_id = dest_account["id"]
            destination_applied = True
            logger.info(f"Destination '{destination}' found: {destination_id}")
        else:
            logger.info(f"Destination '{destination}' not found, skipping")

    # Build payload
    today = datetime.now(pytz.timezone(TIMEZONE)).isoformat()
    transaction = {
        "type": "withdrawal",
        "amount": str(amount),
        "description": description,
        "source_id": source_account["id"],
        "date": today,
    }

    if category_id:
        transaction["category_id"] = category_id
    if destination_id:
        transaction["destination_id"] = destination_id

    payload = {"transactions": [transaction]}

    try:
        response = create_transaction(payload)
        response.raise_for_status()

        # Build confirmation with details
        lines = [
            f"✅ Gasto registrado: *{amount:.2f}* — {description}",
            f"🏦 Origen: {source_account['attributes']['name']}",
        ]
        if category_applied:
            lines.append(f"📂 Categoría: {category}")
        if destination_applied:
            lines.append(f"🎯 Destino: {destination}")

        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
        context.user_data["last_origin"] = origin
    except Exception as e:
        logger.error(f"Error in quick_expense: {e}")
        await update.message.reply_text("❌ Error al registrar el gasto.")


# ─── Cancel ────────────────────────────────────────────────

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel the current conversation and clear user data."""
    logger.info("Canceling expense flow")

    if update.message:
        await update.message.reply_text("❌ Operación cancelada.")
    elif update.callback_query:
        await update.callback_query.message.reply_text("❌ Operación cancelada.")

    # Clear all user data to prevent stale state
    context.user_data.clear()
    return ConversationHandler.END


# ─── Refresh Cache Command ─────────────────────────────────

async def refresh_cache_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manually refresh the cache."""
    if not await require_auth(update, context):
        return

    refresh_cache()
    await update.message.reply_text("✅ Caché refrescado correctamente.")


# ─── ConversationHandler Setup ─────────────────────────────

expense_conv = ConversationHandler(
    entry_points=[
        CommandHandler("expenseButton", start_expense_button),
        CallbackQueryHandler(start_expense_button, pattern="^menu_expense$"),
    ],
    states={
        SELECT_ORIGIN: [
            CallbackQueryHandler(select_origin, pattern="^origin::"),
        ],
        ENTER_AMOUNT_DESC: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, enter_amount_description),
        ],
        SELECT_DESTINATION: [
            CallbackQueryHandler(select_destination, pattern="^dest::"),
        ],
        ENTER_NEW_DEST_NAME: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, enter_new_dest_name),
        ],
        SELECT_CATEGORY: [
            CallbackQueryHandler(select_category, pattern="^cat::"),
        ],
        SELECT_BUDGET: [
            CallbackQueryHandler(select_budget, pattern="^budget::"),
        ],
        SELECT_BILL: [
            CallbackQueryHandler(select_bill, pattern="^bill::"),
        ],
        ENTER_TAGS: [
            CallbackQueryHandler(skip_tags, pattern="^tags::none$"),
            MessageHandler(filters.TEXT & ~filters.COMMAND, enter_tags),
        ],
        CONFIRM_EXPENSE: [
            CallbackQueryHandler(confirm_expense, pattern="^confirm_expense$"),
        ],
    },
    fallbacks=[
        CommandHandler("cancel", cancel),
        CallbackQueryHandler(cancel, pattern="^cancelar$"),
    ],
    per_chat=True,
    per_message=False,  # Default — mixed CallbackQueryHandler + MessageHandler
)

# Export handlers
expense_handlers = [
    CommandHandler("gasto", quick_expense),
    CommandHandler("refresh", refresh_cache_command),
    expense_conv,
]
