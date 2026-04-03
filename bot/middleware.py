"""Authorization middleware and input validation helpers."""
import logging
from typing import Optional

from telegram import Update
from telegram.ext import ContextTypes

from bot.config import ALLOWED_USER_IDS


def is_authorized(user_id: int) -> bool:
    """Check if a user is authorized to use the bot.

    Returns True if ALLOWED_USER_IDS is not configured (open access).
    """
    if not ALLOWED_USER_IDS:
        return True
    return user_id in ALLOWED_USER_IDS


async def require_auth(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> bool:
    """Middleware: reject unauthorized users. Returns True if authorized."""
    user_id = update.effective_user.id
    if not is_authorized(user_id):
        logging.warning(f"Unauthorized access attempt from user_id={user_id}")
        if update.message:
            await update.message.reply_text(
                "❌ No estás autorizado para usar este bot."
            )
        elif update.callback_query:
            await update.callback_query.answer(
                "No estás autorizado para usar este bot.", show_alert=True
            )
        return False
    return True


def sanitize_text(text: str, max_length: int = 255) -> str:
    """Strip whitespace and truncate text to max_length."""
    cleaned = text.strip()
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length]
    return cleaned


def validate_amount(text: str) -> Optional[float]:
    """Parse amount from text. Returns float or None if invalid."""
    try:
        return float(text.replace(",", "."))
    except (ValueError, AttributeError):
        return None
