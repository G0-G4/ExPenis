from bot.messages import *
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ConversationHandler, Application
from bot.bot_config import *
from bot.keyboards import  *
from core.service.account_service import get_user_accounts
from core.service.category_service import ensure_user_has_categories
from core.service.transaction_service import get_todays_totals, get_todays_transactions
from telegram.error import BadRequest
class TransactionEditScreen:

    def __init__(self, application: Application):
        self.income_cats = []
        self.expense_cats = []
        self.select = "✓"
        self.accounts = []
        self.account_id = None
        self.transaction_type = 'expense'
        self.category = None
        application.add_handler(CallbackQueryHandler(self.enter_transaction_handler, pattern='^enter_transaction$'))
        application.add_handler(CallbackQueryHandler(self.account_select_handler, pattern='^account_'))
        application.add_handler(CallbackQueryHandler(self.transaction_type_select_handler, pattern='^type_'))
        application.add_handler(CallbackQueryHandler(self.category_select_handler, pattern='^income_|expense_'))

    async def enter_transaction_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.callback_query.from_user.id
        await self.fetch_data(user_id)
        if len(self.accounts):
            return await self.display_on(update, "accounts", await self.get_accounts_markup(user_id))
        return await self.display_on(update, "no accounts", self.get_no_accounts_markup())


    async def account_select_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.callback_query.from_user.id
        self.account_id = int(update.callback_query.data.split("_")[1])
        await self.display_on(update, "account selected", await self.get_accounts_markup(user_id))

    async def category_select_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.callback_query.from_user.id
        self.category = update.callback_query.data.split("_")[1]
        await self.display_on(update, "category selected", await self.get_accounts_markup(user_id))

    async def transaction_type_select_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.callback_query.from_user.id
        self.transaction_type = update.callback_query.data.split("_")[1]
        self.category = None
        await self.display_on(update, "type selected", await self.get_accounts_markup(user_id))


    async def fetch_data(self, user_id):
        self.accounts = await get_user_accounts(user_id)
        self.income_cats, self.expense_cats = await ensure_user_has_categories(user_id)

    def get_no_accounts_markup(self):
        keyboard = [[InlineKeyboardButton("⬅️ Back", callback_data="back_to_main")]]
        return InlineKeyboardMarkup(keyboard)

    async def get_accounts_markup(self, user_id):
        """Create a keyboard with accounts and their calculated balances"""
        keyboard = []
        row = []
        for i, account in enumerate(self.accounts):
            # Calculate the current balance for this account
            current_balance = await calculate_account_balance(account.id, user_id)
            prefix = self.select if account.id == self.account_id else ""
            row.append(InlineKeyboardButton(f"{account.name} ({format_amount(current_balance)})" + prefix,
                                            callback_data=f'account_{account.id}'))
            if len(row) == CATEGORIES_PER_ROW or i == len(self.accounts) - 1:
                keyboard.append(row)
                row = []
        # Add back button to account selection
        keyboard.extend(self.get_transaction_type_selection_keyboard())
        keyboard.extend(self.get_category_selection_keyboard())
        keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="back")])
        return InlineKeyboardMarkup(keyboard)

    def get_transaction_type_selection_keyboard(self):
        return [
            [
                InlineKeyboardButton(f"🟢 Income (+){self.select if self.transaction_type == 'income' else ''}",
                                     callback_data='type_income'),
                InlineKeyboardButton(f"🔴 Expense (-){self.select if self.transaction_type == 'expense' else ''}",
                                     callback_data='type_expense'),
            ],
        ]

    def get_category_selection_keyboard(self):
        """Create a keyboard with categories arranged in columns"""
        keyboard = []
        row = []
        cats = self.expense_cats if self.transaction_type == 'expense' else self.income_cats
        for i, category in enumerate(cats):
            row.append(InlineKeyboardButton(category.name + self.select if category.name == self.category else category.name, callback_data=f'{self.transaction_type}_{category.name}'))
            if len(row) == CATEGORIES_PER_ROW or i == len(cats) - 1:
                keyboard.append(row)
                row = []
        # Add back button to category selection
        return keyboard

    async def display_on(self, update: Update, text, markup):
        try:
            if update.message:
                await update.message.reply_text(text=text, reply_markup=markup, parse_mode="HTML")
            elif update.callback_query:
                await update.callback_query.edit_message_text(text=text, reply_markup=markup, parse_mode="HTML")
        except BadRequest as e:
            print(f"no modifications {e.message}")
