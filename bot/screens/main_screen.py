

from bot.messages import *
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ConversationHandler, Application
from bot.bot_config import *
from bot.keyboards import  *
from core.service.transaction_service import get_todays_totals, get_todays_transactions

MAIN_SCREEN = 'MAIN_SCREEN'
class MainScreen():
    def __init__(self, application: Application):
        self.net_total = None
        self.total_expense = None
        self.total_income = None
        self.totals = None
        self.todays_transactions = None
        application.add_handler(CommandHandler('start', self.handler))

    async def handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.fetch_data(update.message.from_user.id)
        await self.display_on(update)


    async def fetch_data(self, user_id: int):
        self.todays_transactions = await get_todays_transactions(user_id)
        self.totals = await get_todays_totals(user_id)
        self.total_income = self.totals["total_income"]
        self.total_expense = self.totals["total_expense"]
        self.net_total = self.totals["net_total"]

    def get_markup(self):
        keyboard = []
        for transaction in self.todays_transactions:
            emoji = "🟢" if transaction.type == "income" else "🔴"
            formatted_amount = format_amount(transaction.amount)
            button_text = f"{emoji} {formatted_amount:>10} ({transaction.category})"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f"view_transaction_{transaction.id}")])
        # Add separator if there are transactions
        if self.todays_transactions:
            keyboard.append([InlineKeyboardButton("───────────────", callback_data="separator")])
        # Add main menu button
        keyboard.extend(get_main_menu_keyboard())

        return InlineKeyboardMarkup(keyboard)

    def get_message(self):
        # Build message text with totals
        totals_text = f"\n\n{TOTAL_INCOME_MESSAGE.format(total_income=format_amount(self.total_income))}\n"
        totals_text += f"{TOTAL_EXPENSE_MESSAGE.format(total_expense=format_amount(self.total_expense))}\n"
        if self.net_total >= 0:
            totals_text += f"{NET_TOTAL_MESSAGE.format(net_total=f'+{format_amount(self.net_total)}')}"
        else:
            totals_text += f"{NET_TOTAL_MESSAGE.format(net_total=f'-{format_amount(abs(self.net_total))}')}"

        message_text = WELCOME_MESSAGE
        if self.todays_transactions:
            message_text = f"{WELCOME_MESSAGE}\n\n{TODAYS_TRANSACTIONS_MESSAGE}{totals_text}"
        else:
            message_text = f"{WELCOME_MESSAGE}\n\n{NO_TRANSACTIONS_MESSAGE}{totals_text}"
        return message_text

    async def display_on(self, update: Update):
        if update.message:
            await update.message.reply_text(text=self.get_message(), reply_markup=self.get_markup(), parse_mode="HTML")
        elif update.callback_query:
            await update.callback_query.edit_message_text(text=self.get_message(), reply_markup=self.get_markup(), parse_mode="HTML")

