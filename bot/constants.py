from telegram.ext import ConversationHandler

SELECT_ORIGIN, ENTER_AMOUNT_DESC, SELECT_DESTINATION, ENTER_NEW_DEST_NAME = range(4)
OCULTAR_CUENTAS = ["WiseEmergency", "TrezorBtc"]
OCULTAR_CUENTAS_LOWER = [c.lower() for c in OCULTAR_CUENTAS]
