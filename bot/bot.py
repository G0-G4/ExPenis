from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters
import asyncio

from core.config import TOKEN
from core.service.transaction_service import TransactionService
from core.service.category_service import CategoryService
from core.service.account_service import AccountService
import logging

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

# Define conversation states
ENTER_TRANSACTION, ACCOUNT_SELECTION, SELECT_TYPE, SELECT_CATEGORY, ENTER_AMOUNT, SELECT_PERIOD, VIEW_PERIOD, ENTER_ACCOUNT_NAME, ENTER_ACCOUNT_AMOUNT = range(9)

# UI constants
CATEGORIES_PER_ROW = 3

# Message constants with improved formatting
WELCOME_MESSAGE = "🎯 <b>Welcome to Expense Tracker Bot!</b>\n\nClick the button below to enter a transaction."
TODAYS_TRANSACTIONS_MESSAGE = "📋 <b>Today's Transactions:</b>"
NO_TRANSACTIONS_MESSAGE = "📭 <i>No transactions today.</i>"
TOTAL_INCOME_MESSAGE = "🟢 <b>Total Income:  {total_income}</b>"
TOTAL_EXPENSE_MESSAGE = "🔴 <b>Total Expense: {total_expense}</b>"
NET_TOTAL_MESSAGE = "📊 <b>Net Total:     {net_total}</b>"
TRANSACTION_TYPE_MESSAGE = "CALLTYPE <b>Select transaction type:</b>"
INCOME_CATEGORY_MESSAGE = "💰 <b>Select income category:</b>"
EXPENSE_CATEGORY_MESSAGE = "🛒 <b>Select expense category:</b>"
AMOUNT_PROMPT_MESSAGE = "💵 <b>Please enter the amount:</b>"
INVALID_AMOUNT_MESSAGE = "⚠️ <i>Please enter a valid number for the amount.</i>"
THANK_YOU_MESSAGE = "🙏 <b>Thank you!</b>"
MAIN_MENU_MESSAGE = "📋 <b>What would you like to do next?</b>"
VIEW_TRANSACTIONS_MESSAGE = "📜 <b>Here are your recent transactions:</b>"
TRANSACTION_NOT_FOUND_MESSAGE = "❌ <i>Transaction not found or access denied.</i>"
EDIT_TRANSACTION_MESSAGE = "✏️ <b>Editing transaction:</b>"
CHOOSE_OPTION_MESSAGE = "🔧 <b>Choose an option:</b>"
TRANSACTION_DELETED_MESSAGE = "🗑️ <b>Transaction deleted successfully!</b>"
ERROR_DELETING_TRANSACTION_MESSAGE = "💥 <i>Error deleting transaction.</i>"
TRANSACTION_RECORDED_MESSAGE = "💾 <b>Transaction recorded:</b>"
ERROR_SAVING_TRANSACTION_MESSAGE = "⚠️ <i>Note: Failed to save to database.</i>"
TRANSACTION_UPDATED_MESSAGE = "🔄 <b>Transaction updated:</b>"
ERROR_UPDATING_TRANSACTION_MESSAGE = "💥 <i>Error updating transaction.</i>"
ERROR_NO_TRANSACTION_SELECTED = "❌ <i>Error: No transaction selected for editing.</i>"
TRANSACTION_ID_MESSAGE = "🆔 <b>Transaction ID:</b>"
PERIOD_VIEW_MESSAGE = "📅 <b>Select a period to view:</b>"
PERIOD_STATS_MESSAGE = "📈 <b>Period Statistics</b>"
NO_DATA_MESSAGE = "📭 <i>No data for this period.</i>"
ACCOUNT_SELECTION_MESSAGE = "💳 <b>Select an account:</b>"
NO_ACCOUNTS_MESSAGE = "📭 <i>You don't have any accounts yet. Please create an account first.</i>"

# Account creation messages
ADD_ACCOUNT_MESSAGE = "🏦 <b>Please enter the account name:</b>"
ADD_ACCOUNT_AMOUNT_MESSAGE = "💰 <b>Please enter the initial amount:</b>"
ACCOUNT_CREATED_MESSAGE = "✅ <b>Account created successfully!</b>"

# Helper function to format numbers with thousands separator
def format_amount(amount):
    """Format amount with thousands separator and 2 decimal places"""
    return f"{amount:,.2f}"

# Helper function to format percentage
def format_percentage(value):
    """Format percentage with 1 decimal place"""
    return f"{value:.1f}"


class ExpenseBot:
    def __init__(self):
        self.user_data = {}
        self.account_service = AccountService()
        self.transaction_service = TransactionService(self.account_service)
        self.category_service = CategoryService()
        self.application = None

    def create_category_keyboard(self, categories, prefix):
        """Create a keyboard with categories arranged in columns"""
        keyboard = []
        row = []
        for i, category in enumerate(categories):
            row.append(InlineKeyboardButton(category, callback_data=f'{prefix}_{category}'))
            if len(row) == CATEGORIES_PER_ROW or i == len(categories) - 1:
                keyboard.append(row)
                row = []
        # Add back button to category selection
        keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="back_to_type_selection")])
        return keyboard

    def create_account_keyboard(self, accounts):
        """Create a keyboard with accounts arranged in columns"""
        keyboard = []
        row = []
        for i, account in enumerate(accounts):
            # Display the account name and its calculated balance
            # We'll calculate the balance here instead of using the stored amount
            row.append(InlineKeyboardButton(f"{account.name}", 
                                           callback_data=f'account_{account.id}'))
            if len(row) == CATEGORIES_PER_ROW or i == len(accounts) - 1:
                keyboard.append(row)
                row = []
        # Add back button to account selection
        keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="back_to_main")])
        return keyboard

    async def create_account_keyboard_with_balances(self, accounts, user_id):
        """Create a keyboard with accounts and their calculated balances"""
        keyboard = []
        row = []
        for i, account in enumerate(accounts):
            # Calculate the current balance for this account
            current_balance = await self.account_service.calculate_account_balance(account.id, user_id)
            row.append(InlineKeyboardButton(f"{account.name} ({format_amount(current_balance)})", 
                                           callback_data=f'account_{account.id}'))
            if len(row) == CATEGORIES_PER_ROW or i == len(accounts) - 1:
                keyboard.append(row)
                row = []
        # Add back button to account selection
        keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="back_to_main")])
        return keyboard

    def get_main_menu_keyboard(self):
        """Create the main menu keyboard"""
        return [
            [InlineKeyboardButton("➕ Enter Transaction", callback_data='enter_transaction')],
            [InlineKeyboardButton("📊 View by Period", callback_data='select_period')]
        ]

    def get_transaction_type_keyboard(self):
        """Create the transaction type selection keyboard"""
        return [
            [
                InlineKeyboardButton("🟢 Income (+)", callback_data='type_income'),
                InlineKeyboardButton("🔴 Expense (-)", callback_data='type_expense'),
            ],
            [InlineKeyboardButton("⬅️ Back", callback_data="back_to_account_selection")]
        ]

    def get_period_navigation_keyboard(self, period_type, period_value, user_id):
        """Create navigation keyboard for period viewing"""
        keyboard = []
        
        # Navigation buttons
        nav_row = [
            InlineKeyboardButton("⬅️ Previous", callback_data=f"prev_{period_type}_{period_value}"),
            InlineKeyboardButton("📅 Choose Date", callback_data=f"choose_custom_period"),
            InlineKeyboardButton("Next ➡️", callback_data=f"next_{period_type}_{period_value}")
        ]
        keyboard.append(nav_row)
        
        # Back to period selection
        keyboard.append([InlineKeyboardButton("🔙 Back to Periods", callback_data="select_period")])
        
        return keyboard

    async def show_period_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show period selection menu"""
        keyboard = [
            [InlineKeyboardButton("📅 Today", callback_data="view_period_day_0")],
            [InlineKeyboardButton("📅 This Week", callback_data="view_period_week_0")],
            [InlineKeyboardButton("📅 This Month", callback_data="view_period_month_0")],
            [InlineKeyboardButton("📅 This Year", callback_data="view_period_year_0")],
            [InlineKeyboardButton("🔍 Custom Period", callback_data="choose_custom_period")],
            [InlineKeyboardButton("⬅️ Back", callback_data="back_to_main")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.callback_query:
            await update.callback_query.edit_message_text(
                text=PERIOD_VIEW_MESSAGE,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
        else:
            await update.message.reply_text(
                text=PERIOD_VIEW_MESSAGE,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )

    async def view_period_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                               period_type: str, offset: int = 0):
        """View statistics for a specific period"""
        query = update.callback_query
        user_id = query.from_user.id
        
        # Get period data
        period_data = await self.transaction_service.get_period_statistics(
            user_id, period_type, offset
        )
        
        # Add navigation keyboard - this will be used in both cases
        keyboard = self.get_period_navigation_keyboard(period_type, offset, user_id)
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if not period_data or (not period_data["income_categories"] and not period_data["expense_categories"]):
            await query.edit_message_text(
                text=f"{PERIOD_STATS_MESSAGE}\n\n{NO_DATA_MESSAGE}",
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
            return
        
        # Format message
        message_text = f"{PERIOD_STATS_MESSAGE}\n"
        message_text += f"<pre>Period: {period_data['period_label']}</pre>\n\n"
        
        # Add income categories
        if period_data["income_categories"]:
            message_text += "<b>💰 Income by Category:</b>\n"
            total_income = sum(cat["total"] for cat in period_data["income_categories"])
            for category in period_data["income_categories"]:
                percentage = (category["total"] / total_income * 100) if total_income > 0 else 0
                message_text += f"  {category['category']:<15} {format_amount(category['total']):>12} ({format_percentage(percentage)}%)\n"
            message_text += f"  {'Total Income':<15} <b>{format_amount(total_income):>12}</b>\n\n"
        
        # Add expense categories
        if period_data["expense_categories"]:
            message_text += "<b>💸 Expenses by Category:</b>\n"
            total_expense = sum(cat["total"] for cat in period_data["expense_categories"])
            for category in period_data["expense_categories"]:
                percentage = (category["total"] / total_expense * 100) if total_expense > 0 else 0
                message_text += f"  {category['category']:<15} {format_amount(category['total']):>12} ({format_percentage(percentage)}%)\n"
            message_text += f"  {'Total Expenses':<15} <b>{format_amount(total_expense):>12}</b>\n\n"
        
        # Add net total
        net_total = period_data["net_total"]
        net_total_formatted = format_amount(abs(net_total))
        if net_total >= 0:
            message_text += f"<b>📊 Net Total:       +{net_total_formatted}</b>"
        else:
            message_text += f"<b>📊 Net Total:       -{net_total_formatted}</b>"
        
        await query.edit_message_text(
            text=message_text,
            reply_markup=reply_markup,
            parse_mode="HTML"
        )

    async def get_user_income_categories(self, user_id: int) -> list:
        """Get income category names for a user"""
        categories = await self.category_service.get_user_income_categories(user_id)
        return [cat.name for cat in categories] if categories else []

    async def get_user_expense_categories(self, user_id: int) -> list:
        """Get expense category names for a user"""
        categories = await self.category_service.get_user_expense_categories(user_id)
        return [cat.name for cat in categories] if categories else []

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send welcome message and show main menu with today's transactions"""
        user_id = update.message.from_user.id if update.message else update.callback_query.from_user.id
        
        # Get today's transactions
        todays_transactions = await self.transaction_service.get_todays_transactions(user_id)
        
        # Get today's totals
        totals = await self.transaction_service.get_todays_totals(user_id)
        total_income = totals["total_income"]
        total_expense = totals["total_expense"]
        net_total = totals["net_total"]
        
        keyboard = []
        
        # Add today's transactions as buttons
        for transaction in todays_transactions:
            emoji = "🟢" if transaction.type == "income" else "🔴"
            formatted_amount = format_amount(transaction.amount)
            button_text = f"{emoji} {formatted_amount:>10} ({transaction.category})"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f"edit_{transaction.id}")])
        
        # Add separator if there are transactions
        if todays_transactions:
            keyboard.append([InlineKeyboardButton("───────────────", callback_data="separator")])
        
        # Add main menu button
        keyboard.extend(self.get_main_menu_keyboard())
        
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

    async def add_account(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start the account creation process"""
        user_id = update.message.from_user.id
        
        # Initialize user data for account creation
        if user_id not in self.user_data:
            self.user_data[user_id] = {}
        self.user_data[user_id]['state'] = 'ENTER_ACCOUNT_NAME'
        
        # Ask for account name
        keyboard = [[InlineKeyboardButton("⬅️ Cancel", callback_data="back_to_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            ADD_ACCOUNT_MESSAGE,
            reply_markup=reply_markup,
            parse_mode="HTML"
        )

    async def refresh_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Refresh the main menu view"""
        await self.start(update, context)

    async def edit_transaction(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle transaction editing"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        transaction_id = int(query.data.split('_')[1])
        
        # Get transaction details
        transaction = await self.transaction_service.get_transaction_by_id(transaction_id)
        
        if not transaction or transaction.user_id != user_id:
            await query.edit_message_text(TRANSACTION_NOT_FOUND_MESSAGE, parse_mode="HTML")
            return
        
        # Create edit options
        keyboard = [
            [InlineKeyboardButton("✏️ Edit Amount", callback_data=f"edit_amount_{transaction.id}")],
            [InlineKeyboardButton("🗑️ Delete", callback_data=f"delete_{transaction.id}")],
            [InlineKeyboardButton("⬅️ Back", callback_data="back_to_main")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        emoji = "🟢" if transaction.type == "income" else "🔴"
        formatted_amount = format_amount(transaction.amount)
        transaction_text = f"{emoji} {formatted_amount} ({transaction.category})"
        
        await query.edit_message_text(
            text=f"{EDIT_TRANSACTION_MESSAGE}\n<pre>{transaction_text}</pre>\n\n{CHOOSE_OPTION_MESSAGE}",
            reply_markup=reply_markup,
            parse_mode="HTML"
        )

    async def edit_transaction(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle transaction editing"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        transaction_id = int(query.data.split('_')[1])
        
        # Get transaction details
        transaction = await self.transaction_service.get_transaction_by_id(transaction_id)
        
        if not transaction or transaction.user_id != user_id:
            await query.edit_message_text(TRANSACTION_NOT_FOUND_MESSAGE, parse_mode="HTML")
            return
        
        # Store editing state
        if user_id not in self.user_data:
            self.user_data[user_id] = {}
        self.user_data[user_id]['editing_transaction_id'] = transaction_id
        self.user_data[user_id]['account_id'] = transaction.account_id
        self.user_data[user_id]['type'] = transaction.type
        self.user_data[user_id]['category'] = transaction.category
        self.user_data[user_id]['state'] = 'EDITING_TRANSACTION'
        
        # Show account selection with calculated balances
        accounts = await self.account_service.get_user_accounts(user_id)
        keyboard = await self.create_account_keyboard_with_balances(accounts, user_id)
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text=f"{EDIT_TRANSACTION_MESSAGE}\n<pre>{transaction.to_dict()}</pre>\n\n{ACCOUNT_SELECTION_MESSAGE}",
            reply_markup=reply_markup,
            parse_mode="HTML"
        )

    async def delete_transaction(self, update: Update, context: ContextTypes.DEFAULT_TYPE, transaction_id: int):
        """Delete a transaction"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        
        try:
            # Delete the transaction
            result = await self.transaction_service.delete_transaction(transaction_id, user_id)
            
            if result:
                await query.edit_message_text(TRANSACTION_DELETED_MESSAGE, parse_mode="HTML")
            else:
                await query.edit_message_text(TRANSACTION_NOT_FOUND_MESSAGE, parse_mode="HTML")
        except Exception as e:
            logger.error(f"Error deleting transaction: {e}")
            await query.edit_message_text(ERROR_DELETING_TRANSACTION_MESSAGE, parse_mode="HTML")
        
        # After deletion, show main menu
        await self.refresh_main_menu(update, context)

    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle all button presses"""
        query = update.callback_query
        
        if not query or not query.from_user:
            return
            
        await query.answer()
        
        user_id = query.from_user.id
        
        if query.data == 'enter_transaction':
            # First, show account selection with calculated balances
            accounts = await self.account_service.get_user_accounts(user_id)
            
            if not accounts:
                # Handle case where user has no accounts
                keyboard = [[InlineKeyboardButton("⬅️ Back", callback_data="back_to_main")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(
                    text=NO_ACCOUNTS_MESSAGE,
                    reply_markup=reply_markup,
                    parse_mode="HTML"
                )
                return
            
            # Create account keyboard with calculated balances
            keyboard = await self.create_account_keyboard_with_balances(accounts, user_id)

            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                text=ACCOUNT_SELECTION_MESSAGE,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
        
        elif query.data == 'select_period':
            await self.show_period_selection(update, context)
        
        elif query.data.startswith('view_period_'):
            parts = query.data.split('_')
            period_type = parts[2]  # day, week, month, year
            offset = int(parts[3])  # offset for navigation
            await self.view_period_stats(update, context, period_type, offset)
        
        elif query.data.startswith('prev_') or query.data.startswith('next_'):
            parts = query.data.split('_')
            direction = parts[0]  # prev or next
            period_type = parts[1]
            current_offset = int(parts[2])
            
            # Calculate new offset
            offset = current_offset - 1 if direction == 'prev' else current_offset + 1
            await self.view_period_stats(update, context, period_type, offset)
        
        elif query.data == 'choose_custom_period':
            # Store state for date input
            if user_id not in self.user_data:
                self.user_data[user_id] = {}
            self.user_data[user_id]['state'] = 'CHOOSING_DATE'
            
            # Ask user for date with back button
            keyboard = [[InlineKeyboardButton("⬅️ Back", callback_data="select_period")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                text="📅 <b>Please enter a date in one of these formats:</b>\n"
                     "<pre>YYYY</pre>          (for a year)\n"
                     "<pre>YYYY-MM</pre>       (for a month)\n"
                     "<pre>YYYY-MM-DD</pre>    (for a specific date)",
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
        
        elif query.data.startswith('edit_') and not query.data.startswith('edit_amount_'):
            await self.edit_transaction(update, context)
        
        
        elif query.data.startswith('delete_'):
            transaction_id = int(query.data.split('_')[1])
            await self.delete_transaction(update, context, transaction_id)
        
        elif query.data == 'back_to_main':
            # Refresh the main view with updated transactions
            await self.refresh_main_menu(update, context)
        
        elif query.data == 'back_to_type_selection':
            # Show transaction type selection again
            reply_markup = InlineKeyboardMarkup(self.get_transaction_type_keyboard())
            await query.edit_message_text(
                text=TRANSACTION_TYPE_MESSAGE,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
        
        elif query.data == 'back_to_account_selection':
            # Return to account selection
            accounts = await self.account_service.get_user_accounts(user_id)
            if accounts:
                keyboard = await self.create_account_keyboard_with_balances(accounts, user_id)
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(
                    text=ACCOUNT_SELECTION_MESSAGE,
                    reply_markup=reply_markup,
                    parse_mode="HTML"
                )
        
        elif query.data == 'type_income':
            # Ensure user has categories, creating defaults if needed
            income_cats, _ = await self.category_service.ensure_user_has_categories(user_id)
            user_income_categories = [cat.name for cat in income_cats]
            
            keyboard = self.create_category_keyboard(user_income_categories, 'income')
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                text=INCOME_CATEGORY_MESSAGE,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
            
            # Store transaction type for this user
            if user_id not in self.user_data:
                self.user_data[user_id] = {}
            self.user_data[user_id]['type'] = 'income'
        
        elif query.data == 'type_expense':
            # Ensure user has categories, creating defaults if needed
            _, expense_cats = await self.category_service.ensure_user_has_categories(user_id)
            user_expense_categories = [cat.name for cat in expense_cats]
            
            keyboard = self.create_category_keyboard(user_expense_categories, 'expense')
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                text=EXPENSE_CATEGORY_MESSAGE,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
            
            # Store transaction type for this user
            if user_id not in self.user_data:
                self.user_data[user_id] = {}
            self.user_data[user_id]['type'] = 'expense'
        
        elif query.data.startswith('account_'):
            account_id = int(query.data.split('_')[1])
            
            # Store selected account
            if user_id not in self.user_data:
                self.user_data[user_id] = {}
            self.user_data[user_id]['account_id'] = account_id
            
            # Now show transaction type selection
            reply_markup = InlineKeyboardMarkup(self.get_transaction_type_keyboard())
            await query.edit_message_text(
                text=TRANSACTION_TYPE_MESSAGE,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
        
        elif query.data and (query.data.startswith('income_') or query.data.startswith('expense_')):
            # Category selected, ask for amount
            if query.data:
                parts = query.data.split('_', 1)  # Split only on first underscore
                category_type = parts[0]
                category = parts[1]  # Now using category name directly
                
                # Store selected category
                self.user_data[user_id]['category'] = category
                
                # Add back button to amount prompt
                keyboard = [[InlineKeyboardButton("⬅️ Back", callback_data="back_to_type_selection")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    text=f"🏷️ <b>Selected category: {category}</b>\n\n{AMOUNT_PROMPT_MESSAGE}",
                    reply_markup=reply_markup,
                    parse_mode="HTML"
                )
                
                # Set state to expect amount input
                self.user_data[user_id]['state'] = ENTER_AMOUNT

    async def handle_amount(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle amount input from user"""
        if not update.message or not update.message.from_user:
            return
            
        user_id = update.message.from_user.id
        
        # Handle account name input
        if user_id in self.user_data and self.user_data[user_id].get('state') == 'ENTER_ACCOUNT_NAME':
            account_name = update.message.text.strip()
            if not account_name:
                keyboard = [[InlineKeyboardButton("⬅️ Cancel", callback_data="back_to_main")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    "⚠️ <i>Please enter a valid account name.</i>",
                    reply_markup=reply_markup,
                    parse_mode="HTML"
                )
                return
                
            # Store account name
            self.user_data[user_id]['account_name'] = account_name
            self.user_data[user_id]['state'] = 'ENTER_ACCOUNT_AMOUNT'
            
            # Ask for initial amount
            keyboard = [[InlineKeyboardButton("⬅️ Cancel", callback_data="back_to_main")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                ADD_ACCOUNT_AMOUNT_MESSAGE,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
            return
        
        # Handle account amount input
        if user_id in self.user_data and self.user_data[user_id].get('state') == 'ENTER_ACCOUNT_AMOUNT':
            try:
                amount_text = update.message.text.strip()
                initial_amount = float(amount_text) if amount_text else 0.0
                
                # Create the account
                account_name = self.user_data[user_id]['account_name']
                account = await self.account_service.create_account(
                    user_id=user_id,
                    name=account_name,
                    initial_amount=initial_amount
                )
                
                keyboard = [[InlineKeyboardButton("⬅️ Back", callback_data="back_to_main")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    f"{ACCOUNT_CREATED_MESSAGE}\n\n"
                    f"🏦 <b>Account:</b> {account.name}\n"
                    f"💰 <b>Initial Amount:</b> {format_amount(initial_amount)}",
                    reply_markup=reply_markup,
                    parse_mode="HTML"
                )
                
                # Clear user data
                self.user_data[user_id] = {}
                
                # Refresh main menu
                await self.refresh_main_menu(update, context)
                return
                
            except ValueError:
                keyboard = [[InlineKeyboardButton("⬅️ Cancel", callback_data="back_to_main")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    INVALID_AMOUNT_MESSAGE,
                    reply_markup=reply_markup,
                    parse_mode="HTML"
                )
                return
        
        # Check if we're expecting a date input
        if (user_id in self.user_data and 
            self.user_data[user_id].get('state') == 'CHOOSING_DATE'):
            
            date_input = update.message.text.strip()
            
            # Determine period type based on input format
            if len(date_input) == 4 and date_input.isdigit():
                # YYYY format - year
                period_type = 'year'
            elif (len(date_input) == 7 and 
                  date_input[4] == '-' and 
                  date_input[:4].isdigit() and 
                  date_input[5:].isdigit()):
                # YYYY-MM format - month
                period_type = 'month'
            elif (len(date_input) == 10 and 
                  date_input[4] == '-' and 
                  date_input[7] == '-' and 
                  date_input[:4].isdigit() and 
                  date_input[5:7].isdigit() and 
                  date_input[8:].isdigit()):
                # YYYY-MM-DD format - day
                period_type = 'day'
            else:
                keyboard = [[InlineKeyboardButton("⬅️ Back", callback_data="select_period")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    "❌ <b>Invalid date format.</b> Please use one of these formats:\n"
                    "<pre>YYYY</pre>          (for a year)\n"
                    "<pre>YYYY-MM</pre>       (for a month)\n"
                    "<pre>YYYY-MM-DD</pre>    (for a specific date)",
                    reply_markup=reply_markup,
                    parse_mode="HTML"
                )
                return
            
            try:
                # Parse the date input and show stats for that period
                period_data = await self.transaction_service.get_custom_period_statistics(
                    user_id, period_type, date_input
                )
                
                # Add navigation keyboard for custom periods
                keyboard = self.get_period_navigation_keyboard(period_type, 0, user_id)
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                if not period_data or (not period_data["income_categories"] and not period_data["expense_categories"]):
                    await update.message.reply_text(
                        text=f"{PERIOD_STATS_MESSAGE}\n\n{NO_DATA_MESSAGE}",
                        reply_markup=reply_markup,
                        parse_mode="HTML"
                    )
                    self.user_data[user_id] = {}
                    return
                
                # Format message
                message_text = f"{PERIOD_STATS_MESSAGE}\n"
                message_text += f"<pre>Period: {period_data['period_label']}</pre>\n\n"
                
                # Add income categories
                if period_data["income_categories"]:
                    message_text += "<b>💰 Income by Category:</b>\n"
                    total_income = sum(cat["total"] for cat in period_data["income_categories"])
                    for category in period_data["income_categories"]:
                        percentage = (category["total"] / total_income * 100) if total_income > 0 else 0
                        message_text += f"  {category['category']:<15} {format_amount(category['total']):>12} ({format_percentage(percentage)}%)\n"
                    message_text += f"  {'Total Income':<15} <b>{format_amount(total_income):>12}</b>\n\n"
                
                # Add expense categories
                if period_data["expense_categories"]:
                    message_text += "<b>💸 Expenses by Category:</b>\n"
                    total_expense = sum(cat["total"] for cat in period_data["expense_categories"])
                    for category in period_data["expense_categories"]:
                        percentage = (category["total"] / total_expense * 100) if total_expense > 0 else 0
                        message_text += f"  {category['category']:<15} {format_amount(category['total']):>12} ({format_percentage(percentage)}%)\n"
                    message_text += f"  {'Total Expenses':<15} <b>{format_amount(total_expense):>12}</b>\n\n"
                
                # Add net total
                net_total = period_data["net_total"]
                net_total_formatted = format_amount(abs(net_total))
                if net_total >= 0:
                    message_text += f"<b>📊 Net Total:       +{net_total_formatted}</b>"
                else:
                    message_text += f"<b>📊 Net Total:       -{net_total_formatted}</b>"
                
                await update.message.reply_text(
                    text=message_text,
                    reply_markup=reply_markup,
                    parse_mode="HTML"
                )
                
                self.user_data[user_id] = {}
                return
                
            except ValueError as e:
                keyboard = [[InlineKeyboardButton("⬅️ Back", callback_data="select_period")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    "❌ <b>Invalid date format.</b> Please try again.", 
                    reply_markup=reply_markup,
                    parse_mode="HTML"
                )
                return
        
        # Check if we're expecting an amount input for a new transaction
        if user_id in self.user_data and self.user_data[user_id].get('state') == ENTER_AMOUNT:
            try:
                amount_text = update.message.text
                if not amount_text:
                    keyboard = [[InlineKeyboardButton("⬅️ Back", callback_data="back_to_type_selection")]]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    await update.message.reply_text(
                        INVALID_AMOUNT_MESSAGE, 
                        reply_markup=reply_markup,
                        parse_mode="HTML"
                    )
                    return
                    
                amount = float(amount_text)
                
                # Get transaction details
                transaction_type = self.user_data[user_id]['type']
                category = self.user_data[user_id]['category']
                
                # Format transaction for display
                formatted_amount = format_amount(amount)
                if transaction_type == 'income':
                    transaction_text = f"🟢 Income: +{formatted_amount} ({category})"
                else:
                    transaction_text = f"🔴 Expense: -{formatted_amount} ({category})"
                
                # Save transaction to database using transaction service
                try:
                    transaction = await self.transaction_service.create_transaction(
                        user_id=user_id,
                        amount=amount,
                        category=category,
                        transaction_type=transaction_type,
                        account_id=self.user_data[user_id]['account_id']
                    )
                    
                    keyboard = [[InlineKeyboardButton("⬅️ Back", callback_data="back_to_main")]]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    await update.message.reply_text(
                        f"{TRANSACTION_RECORDED_MESSAGE}\n<pre>{transaction_text}</pre>\n\n{TRANSACTION_ID_MESSAGE} {transaction.id}\n\n{THANK_YOU_MESSAGE}",
                        reply_markup=reply_markup,
                        parse_mode="HTML"
                    )
                except Exception as e:
                    logger.error(f"Error saving transaction: {e}")
                    keyboard = [[InlineKeyboardButton("⬅️ Back", callback_data="back_to_main")]]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    await update.message.reply_text(
                        f"{TRANSACTION_RECORDED_MESSAGE}\n<pre>{transaction_text}</pre>\n\n{ERROR_SAVING_TRANSACTION_MESSAGE}\n\n{THANK_YOU_MESSAGE}",
                        reply_markup=reply_markup,
                        parse_mode="HTML"
                    )
                
                # Clear user data for this transaction
                self.user_data[user_id] = {}
                
                # Show main menu with today's transactions
                await self.refresh_main_menu(update, context)
                
            except ValueError:
                keyboard = [[InlineKeyboardButton("⬅️ Back", callback_data="back_to_type_selection")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    INVALID_AMOUNT_MESSAGE, 
                    reply_markup=reply_markup,
                    parse_mode="HTML"
                )
        
        # Check if we're editing an existing transaction
        elif user_id in self.user_data and self.user_data[user_id].get('state') == 'EDITING_TRANSACTION':
            try:
                amount_text = update.message.text
                if not amount_text:
                    keyboard = [[InlineKeyboardButton("⬅️ Back", callback_data="back_to_main")]]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    await update.message.reply_text(
                        INVALID_AMOUNT_MESSAGE, 
                        reply_markup=reply_markup,
                        parse_mode="HTML"
                    )
                    return
                    
                amount = float(amount_text)
                transaction_id = self.user_data[user_id].get('editing_transaction_id')
                
                if not transaction_id:
                    keyboard = [[InlineKeyboardButton("⬅️ Back", callback_data="back_to_main")]]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    await update.message.reply_text(
                        ERROR_NO_TRANSACTION_SELECTED, 
                        reply_markup=reply_markup,
                        parse_mode="HTML"
                    )
                    return
                
                # Get transaction details for display
                transaction_type = self.user_data[user_id]['type']
                category = self.user_data[user_id]['category']
                account_id = self.user_data[user_id]['account_id']
                
                # Format transaction for display
                formatted_amount = format_amount(amount)
                if transaction_type == 'income':
                    transaction_text = f"🟢 Income: +{formatted_amount} ({category})"
                else:
                    transaction_text = f"🔴 Expense: -{formatted_amount} ({category})"
                
                # Update transaction in database
                try:
                    updated_transaction = await self.transaction_service.update_transaction(
                        transaction_id=transaction_id,
                        user_id=user_id,
                        amount=amount,
                        category=category,
                        transaction_type=transaction_type,
                        account_id=account_id
                    )
                    
                    if updated_transaction:
                        keyboard = [[InlineKeyboardButton("⬅️ Back", callback_data="back_to_main")]]
                        reply_markup = InlineKeyboardMarkup(keyboard)
                        
                        await update.message.reply_text(
                            f"{TRANSACTION_UPDATED_MESSAGE}\n<pre>{transaction_text}</pre>\n\n{THANK_YOU_MESSAGE}",
                            reply_markup=reply_markup,
                            parse_mode="HTML"
                        )
                    else:
                        keyboard = [[InlineKeyboardButton("⬅️ Back", callback_data="back_to_main")]]
                        reply_markup = InlineKeyboardMarkup(keyboard)
                        
                        await update.message.reply_text(
                            TRANSACTION_NOT_FOUND_MESSAGE, 
                            reply_markup=reply_markup,
                            parse_mode="HTML"
                        )
                except Exception as e:
                    logger.error(f"Error updating transaction: {e}")
                    keyboard = [[InlineKeyboardButton("⬅️ Back", callback_data="back_to_main")]]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    await update.message.reply_text(
                        ERROR_UPDATING_TRANSACTION_MESSAGE, 
                        reply_markup=reply_markup,
                        parse_mode="HTML"
                    )
                
                # Clear user data
                self.user_data[user_id] = {}
                
                # Show main menu with today's transactions
                await self.refresh_main_menu(update, context)
                
            except ValueError:
                keyboard = [[InlineKeyboardButton("⬅️ Back", callback_data="back_to_main")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    INVALID_AMOUNT_MESSAGE, 
                    reply_markup=reply_markup,
                    parse_mode="HTML"
                )
        else:
            # If not in amount input state, show main menu
            await self.refresh_main_menu(update, context)

    async def set_bot_commands(self):
        """Set bot commands menu"""
        commands = [
            BotCommand("start", "Open the main menu"),
            BotCommand("add_account", "Create a new account"),
        ]
        await self.application.bot.set_my_commands(commands)

    def _initialize_application(self):
        """Initialize the Telegram application and register handlers"""
        if not TOKEN:
            logger.error("TOKEN is not set. Please check your .env file.")
            return False
            
        self.application = ApplicationBuilder().token(TOKEN).build()
        
        # Register command handlers
        self.application.add_handler(CommandHandler('start', self.start))
        self.application.add_handler(CommandHandler('add_account', self.add_account))
        
        # Register callback query handler
        self.application.add_handler(CallbackQueryHandler(self.button_handler))
        
        # Register message handler
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_amount))
        
        return True

    async def post_init(self, application):
        """Post initialization tasks"""
        await self.set_bot_commands()

    def run(self):
        """Run the bot"""
        if not self._initialize_application():
            return
        self.application.post_init = self.post_init
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)


def main():
    """Run the bot."""
    bot = ExpenseBot()
    bot.run()


if __name__ == '__main__':
    main()
