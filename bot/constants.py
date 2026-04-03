from telegram.ext import ConversationHandler

# Conversation states for expense flow
SELECT_ORIGIN, ENTER_AMOUNT_DESC, SELECT_DESTINATION, ENTER_NEW_DEST_NAME = range(4)
SELECT_CATEGORY, SELECT_BUDGET, ENTER_TAGS, CONFIRM_EXPENSE = range(4, 8)
