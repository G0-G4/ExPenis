

from bot.messages import *
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ConversationHandler, Application
from bot.bot_config import *
from bot.keyboards import  *
from core.service.transaction_service import get_todays_totals, get_todays_transactions

MAIN_SCREEN = 'MAIN_SCREEN'
class MainScreen():
    def __init__(self, application: Application):
        application.add_handler(CommandHandler('start', self.handler))

    async def handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.message.from_user.id
        await self.fetch_data(user_id, context)
        await self.display_on(update, context)

    async def fetch_data(self, user_id: int, context: ContextTypes.DEFAULT_TYPE):
        todays_transactions = await get_todays_transactions(user_id)
        totals = await get_todays_totals(user_id)
        
        # Store user-specific data in context.user_data
        context.user_data['todays_transactions'] = todays_transactions
        context.user_data['totals'] = totals
        context.user_data['total_income'] = totals["total_income"]
        context.user_data['total_expense'] = totals["total_expense"]
        context.user_data['net_total'] = totals["net_total"]

    def get_markup(self, context: ContextTypes.DEFAULT_TYPE):
        keyboard = []
        todays_transactions = context.user_data.get('todays_transactions', [])
        
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

        return InlineKeyboardMarkup(keyboard)

    def get_message(self, context: ContextTypes.DEFAULT_TYPE):
        # Get user-specific data
        total_income = context.user_data.get('total_income', 0)
        total_expense = context.user_data.get('total_expense', 0)
        net_total = context.user_data.get('net_total', 0)
        todays_transactions = context.user_data.get('todays_transactions', [])
        
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
        return message_text

    async def display_on(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.message:
            await update.message.reply_text(text=self.get_message(context), reply_markup=self.get_markup(context), parse_mode="HTML")
        elif update.callback_query:
            await update.callback_query.edit_message_text(text=self.get_message(context), reply_markup=self.get_markup(context), parse_mode="HTML")

