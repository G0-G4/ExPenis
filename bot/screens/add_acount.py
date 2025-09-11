from os import supports_effective_ids

from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ConversationHandler

from bot.screens.category_selection import CATEGORY_SELECTION_SCREEN
from bot.screens.main import start
from core.helpers import format_percentage
from bot.messages import *
from bot.bot_config import *
from bot.keyboards import  *
from core.config import TOKEN
from core.service.transaction_service import get_todays_totals, get_todays_transactions
from core.service.account_service import AccountService, create_account

ADD_ACCOUNT_SCREEN = 'ADD_ACCOUNT_SCREEN'
async def add_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the account creation process"""
    push_state(context)

    await update.callback_query.edit_message_text(
        ADD_ACCOUNT_MESSAGE,
        parse_mode="HTML"
    )
    context.user_data['previous_state'] = ADD_ACCOUNT_SCREEN
    return ADD_ACCOUNT_SCREEN

ACCOUNT_NAME = 'ACCOUNT_NAME'
async def account_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    push_state(context)

    # Handle account name input
    account_name = update.message.text.strip()
    if not account_name:
        keyboard = [[InlineKeyboardButton("⬅️ back", callback_data="back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.callback_query.edit_message_text(
            "⚠️ <i>Please enter a valid account name.</i>",
            reply_markup=reply_markup,
            parse_mode="HTML"
        )
        return ACCOUNT_NAME

    # Store account name
    context.user_data['account_name'] = account_name
    # Ask for initial amount
    keyboard = [[InlineKeyboardButton("⬅️ back", callback_data="back")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.callback_query.edit_message_text(
        ADD_ACCOUNT_AMOUNT_MESSAGE,
        reply_markup=reply_markup,
        parse_mode="HTML"
    )
    context.user_data['previous_state'] = ACCOUNT_NAME
    return ACCOUNT_NAME

async def create_account_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.callback_query.from_user.id
    try:
        amount_text = update.message.text.strip()
        initial_amount = float(amount_text) if amount_text else 0.0

        # Create the account
        account_name = context.user_data['account_name']
        account = await create_account(
            user_id=user_id,
            name=account_name,
            initial_amount=initial_amount
        )

        keyboard = [[InlineKeyboardButton("⬅️ Back", callback_data="back_to_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.callback_query.edit_message_text(
            f"{ACCOUNT_CREATED_MESSAGE}\n\n"
            f"🏦 <b>Account:</b> {account.name}\n"
            f"💰 <b>Initial Amount:</b> {format_amount(initial_amount)}",
            reply_markup=reply_markup,
            parse_mode="HTML"
        )

        return start(update, context)

    except ValueError:
        keyboard = [[InlineKeyboardButton("⬅️ back", callback_data="back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            INVALID_AMOUNT_MESSAGE,
            reply_markup=reply_markup,
            parse_mode="HTML"
        )
        return