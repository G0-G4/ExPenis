from cmath import acosh
from os import supports_effective_ids

from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ConversationHandler

from core.helpers import format_percentage
from bot.messages import *
from bot.bot_config import *
from bot.keyboards import  *
from core.config import TOKEN
from core.service.transaction_service import get_todays_totals, get_todays_transactions
from core.service.account_service import AccountService
TRANSACTION_TYPE_SELECTION_SCREEN = 'TRANSACTION_TYPE_SELECTION_SCREEN'
async def transaction_type_selection_screen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    push_state(context)
    query = update.callback_query
    await query.answer()
    account_id = query.data.split('_')[1] if query.data != 'back' else context.user_data['account_id']
    context.user_data['account_id'] = account_id

    user_id = query.from_user.id
    reply_markup = InlineKeyboardMarkup(get_transaction_type_keyboard())
    await query.edit_message_text(
        text=TRANSACTION_TYPE_MESSAGE,
        reply_markup=reply_markup,
        parse_mode="HTML")

    context.user_data['previous_state'] = TRANSACTION_TYPE_SELECTION_SCREEN
    return TRANSACTION_TYPE_SELECTION_SCREEN