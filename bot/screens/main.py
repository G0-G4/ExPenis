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

MAIN_SCREEN = 'MAIN_SCREEN'
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    push_state(context)
    context.user_data.clear()
    """Send welcome message and show main menu with today's transactions"""
    user_id = update.message.from_user.id if update.message else update.callback_query.from_user.id

    # Get today's transactions
    todays_transactions = await get_todays_transactions(user_id)

    # Get today's totals
    totals = await get_todays_totals(user_id)
    total_income = totals["total_income"]
    total_expense = totals["total_expense"]
    net_total = totals["net_total"]

    keyboard = []

    # Add today's transactions as buttons
    for transaction in todays_transactions:
        emoji = "🟢" if transaction.type == "income" else "🔴"
        formatted_amount = format_amount(transaction.amount)
        button_text = f"{emoji} {formatted_amount:>10} ({transaction.category})"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"view_transaction_{transaction.id}")])

    # Add separator if there are transactions
    if todays_transactions:
        keyboard.append([InlineKeyboardButton("───────────────", callback_data="separator")])

    # Add main menu button
    keyboard.extend(get_main_menu_keyboard())

    reply_markup = InlineKeyboardMarkup(keyboard)

    # Build message text with totals
    totals_text = f"\n\n{TOTAL_INCOME_MESSAGE.format(total_income=format_amount(total_income))}\n"
    totals_text += f"{TOTAL_EXPENSE_MESSAGE.format(total_expense=format_amount(total_expense))}\n"
    if net_total >= 0:
        totals_text += f"{NET_TOTAL_MESSAGE.format(net_total=f'+{format_amount(net_total)}')}"
    else:
        totals_text += f"{NET_TOTAL_MESSAGE.format(net_total=f'-{format_amount(abs(net_total))}')}"

    message_text = WELCOME_MESSAGE
    if todays_transactions:
        message_text = f"{WELCOME_MESSAGE}\n\n{TODAYS_TRANSACTIONS_MESSAGE}{totals_text}"
    else:
        message_text = f"{WELCOME_MESSAGE}\n\n{NO_TRANSACTIONS_MESSAGE}{totals_text}"

    if update.message:
        await update.message.reply_text(message_text, reply_markup=reply_markup, parse_mode="HTML")
    elif update.callback_query:
        await update.callback_query.edit_message_text(text=message_text, reply_markup=reply_markup, parse_mode="HTML")
    context.user_data['previous_state'] = MAIN_SCREEN
    return MAIN_SCREEN