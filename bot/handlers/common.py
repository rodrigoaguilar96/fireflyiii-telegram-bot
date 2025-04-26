from telegram import Update
from telegram.ext import ContextTypes

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
