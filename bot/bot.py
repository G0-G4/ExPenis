from cmath import acosh

from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ConversationHandler

from core.helpers import format_percentage
from bot.messages import *
from bot.bot_config import *
from bot.keyboards import  *
from core.config import TOKEN
from core.service.transaction_service import TransactionService
from core.service.category_service import CategoryService
from core.service.account_service import AccountService
# import logging

# Enable logging
# logging.basicConfig(
#     format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
# )
# logger = logging.getLogger(__name__)
# logging.getLogger('sqlalchemy.engine').setLevel(logging.ERROR)

ACCOUNT_SELECTION_SCREEN, ACCOUNT_SELECTION, SELECT_TYPE, SELECT_CATEGORY, ENTER_AMOUNT, SELECT_PERIOD, VIEW_PERIOD, ENTER_ACCOUNT_NAME, ENTER_ACCOUNT_AMOUNT, MAIN_SCREEN, TRANSACTION_TYPE_SELECTION_SCREEN, CATEGORY_SELECTION_SCREEN, MONEY_INPUT_SCREEN, TRANSACTION_VIEW_SCREEN= range(
    14)


class ExpenseBot:
    def __init__(self):
        self.user_data = {}
        self.account_service = AccountService()
        self.transaction_service = TransactionService(self.account_service)
        self.category_service = CategoryService()
        self.application = None


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
        keyboard = get_period_navigation_keyboard(period_type, offset, user_id)
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
        self.push_state(context)
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
        return MAIN_SCREEN

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

    async def transaction_view_screen(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle transaction editing"""
        self.push_state(TRANSACTION_VIEW_SCREEN)
        query = update.callback_query
        await query.answer()

        # TODO get values from context not call_back
        user_id = query.from_user.id
        transaction_id = int(query.data.split('_')[2])
        
        # Get transaction details
        transaction = await self.transaction_service.get_transaction_by_id(transaction_id)
        
        if not transaction or transaction.user_id != user_id:
            await query.edit_message_text(TRANSACTION_NOT_FOUND_MESSAGE, parse_mode="HTML")
            return
        
        # Create edit options
        keyboard = [
            [InlineKeyboardButton("✏️ Edit Transaction", callback_data=f"edit_transaction_{transaction.id}")],
            [InlineKeyboardButton("🗑️ Delete", callback_data=f"delete_{transaction.id}")],
            [InlineKeyboardButton("⬅️ Back", callback_data="back")]
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
        context.user_data['previous_state'] = TRANSACTION_VIEW_SCREEN
        return TRANSACTION_VIEW_SCREEN

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

    def get_previous_state(self, context: ContextTypes.DEFAULT_TYPE):
        if len(context.user_data['stack']) == 0:
            return MAIN_SCREEN
        state = context.user_data['stack'].pop()
        print("poped from stack -> " + str(context.user_data['stack']))
        return state

    def push_state(self, context: ContextTypes.DEFAULT_TYPE):
        if not 'stack' in context.user_data:
            context.user_data['previous_state'] = MAIN_SCREEN
            context.user_data['stack'] = []
            context.user_data['set_previous'] = True
        if context.user_data['set_previous']:
            if len(context.user_data['stack']) != 0 and context.user_data['stack'][-1] == context.user_data['previous_state']:
                return
            context.user_data['stack'].append(context.user_data['previous_state'])
            print("pushed to stack -> " + str(context.user_data['stack']))
        else:
            context.user_data['set_previous'] = True

    async def back_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()

        # Get previous state from user_data
        previous_state = self.get_previous_state(context)
        context.user_data['set_previous'] = False

        # Handle going back to previous state
        if previous_state == MAIN_SCREEN:
            return await self.start(update, context)
        if previous_state == ACCOUNT_SELECTION_SCREEN:
            return await self.account_selection_screen(update, context)
        elif previous_state == TRANSACTION_TYPE_SELECTION_SCREEN:
            return await self.transaction_type_selection_screen(update, context)
        elif previous_state == CATEGORY_SELECTION_SCREEN:
            return await self.category_selection_screen(update, context)

        return previous_state

    async def account_selection_screen(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.push_state(context)
        query = update.callback_query
        await query.answer()

        user_id = query.from_user.id
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
            return MAIN_SCREEN

        # Create account keyboard with calculated balances
        keyboard = await create_account_keyboard_with_balances(accounts, user_id, self.account_service)

        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            text=ACCOUNT_SELECTION_MESSAGE,
            reply_markup=reply_markup,
            parse_mode="HTML"
        )
        context.user_data['previous_state'] = ACCOUNT_SELECTION_SCREEN
        return ACCOUNT_SELECTION_SCREEN



    # async def account_selection_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    #     query = update.callback_query
    #     await query.answer()
    #
    #     user_id = query.from_user.id
    #     accounts = await self.account_service.get_user_accounts(user_id)
    #     if not accounts:
    #         keyboard = [[InlineKeyboardButton("⬅️ Back", callback_data="back")]]
    #         reply_markup = InlineKeyboardMarkup(keyboard)
    #         await query.edit_message_text(
    #             text=NO_ACCOUNTS_MESSAGE,
    #             reply_markup=reply_markup,
    #             parse_mode="HTML"
    #         )
    #         return ACCOUNT_SELECTION
    #     keyboard = await create_account_keyboard_with_balances(accounts, user_id, self.account_service)
    #
    #     reply_markup = InlineKeyboardMarkup(keyboard)
    #     await query.edit_message_text(
    #         text=ACCOUNT_SELECTION_MESSAGE,
    #         reply_markup=reply_markup,
    #         parse_mode="HTML"
    #     )
    #     context.user_data['previous_state'] = MAIN
    #     return ACCOUNT_SELECTION

    async def transaction_type_selection_screen(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.push_state(context)
        query = update.callback_query
        await query.answer()

        user_id = query.from_user.id
        reply_markup = InlineKeyboardMarkup(get_transaction_type_keyboard())
        await query.edit_message_text(
            text=TRANSACTION_TYPE_MESSAGE,
            reply_markup=reply_markup,
            parse_mode="HTML")

        context.user_data['previous_state'] = TRANSACTION_TYPE_SELECTION_SCREEN
        return TRANSACTION_TYPE_SELECTION_SCREEN

    async def category_selection_screen(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.push_state(context)
        query = update.callback_query
        await query.answer()
        # TODO get type
        user_id = query.from_user.id

        income_cats, expense_cats = await self.category_service.ensure_user_has_categories(user_id)
        user_income_categories = [cat.name for cat in income_cats]

        keyboard = create_category_keyboard(user_income_categories, 'income')
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

        context.user_data['previous_state'] = CATEGORY_SELECTION_SCREEN
        return CATEGORY_SELECTION_SCREEN

    async def money_input_screen(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()

        user_id = query.from_user.id
        keyboard = [[InlineKeyboardButton("⬅️ Back", callback_data="back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        category = "category"
        await query.edit_message_text(
            text=f"🏷️ <b>Selected category: {category}</b>\n\n{AMOUNT_PROMPT_MESSAGE}",
            reply_markup=reply_markup,
            parse_mode="HTML"
        )
        user_id = update.message.from_user.id
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

            # Show main menu with today's transaction

            return await self.start(update, context)

        except ValueError:
            keyboard = [[InlineKeyboardButton("⬅️ Back", callback_data="back_to_type_selection")]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(
                INVALID_AMOUNT_MESSAGE,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )

    # async def category_selection_screen_expense(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    #     query = update.callback_query
    #     await query.answer()
    #
    #     user_id = query.from_user.id
    #
    #     _, expense_cats = await self.category_service.ensure_user_has_categories(user_id)
    #     user_income_categories = [cat.name for cat in expense_cats]
    #
    #     keyboard = create_category_keyboard(user_income_categories, 'expense')
    #     reply_markup = InlineKeyboardMarkup(keyboard)
    #     await query.edit_message_text(
    #         text=INCOME_CATEGORY_MESSAGE,
    #         reply_markup=reply_markup,
    #         parse_mode="HTML"
    #     )
    #
    #     # Store transaction type for this user
    #     if user_id not in self.user_data:
    #         self.user_data[user_id] = {}
    #     self.user_data[user_id]['type'] = 'expense'
    #
    #     context.user_data['previous_state'] = TRANSACTION_TYPE_SELECTION_SCREEN
    #     return CATEGORY_SELECTION_SCREEN

    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle all button presses"""
        query = update.callback_query
        
        if not query or not query.from_user:
            return
            
        await query.answer()
        


        # Create account keyboard with calculated balances
        # accounts = await self.account_service.get_user_accounts(user_id)
        # if not accounts:
        #     keyboard = [[InlineKeyboardButton("⬅️ Back", callback_data="back_to_main")]]
        #     reply_markup = InlineKeyboardMarkup(keyboard)
        #     await query.edit_message_text(
        #         text=NO_ACCOUNTS_MESSAGE,
        #         reply_markup=reply_markup,
        #         parse_mode="HTML"
        #     )
        #     return MAIN
        # keyboard = await create_account_keyboard_with_balances(accounts, user_id, self.account_service)
        #
        # reply_markup = InlineKeyboardMarkup(keyboard)
        # await query.edit_message_text(
        #     text=ACCOUNT_SELECTION_MESSAGE,
        #     reply_markup=reply_markup,
        #     parse_mode="HTML"
        # )
        # return ACCOUNT_SELECTION
        
        # if query.data == 'enter_transaction':
            # First, show account selection with calculated balances
            # accounts = await self.account_service.get_user_accounts(user_id)
            #
            # if not accounts:
            #     # Handle case where user has no accounts
            #     keyboard = [[InlineKeyboardButton("⬅️ Back", callback_data="back_to_main")]]
            #     reply_markup = InlineKeyboardMarkup(keyboard)
            #     await query.edit_message_text(
            #         text=NO_ACCOUNTS_MESSAGE,
            #         reply_markup=reply_markup,
            #         parse_mode="HTML"
            #     )
            #     return
            #
            # # Create account keyboard with calculated balances
            # keyboard = await create_account_keyboard_with_balances(accounts, user_id, self.account_service)
            #
            # reply_markup = InlineKeyboardMarkup(keyboard)
            # await query.edit_message_text(
            #     text=ACCOUNT_SELECTION_MESSAGE,
            #     reply_markup=reply_markup,
            #     parse_mode="HTML"
            # )
            # return ACCOUNT_SELECTION

        if query.data == 'select_period':
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
        
        elif query.data.startswith('edit_') and not query.data.startswith('edit_amount_') and not query.data.startswith('edit_full_'):
            await self.transaction_view_screen(update, context)
        
        elif query.data.startswith('edit_full_'):
            transaction_id = int(query.data.split('_')[2])
            
            # Get transaction details
            transaction = await self.transaction_service.get_transaction_by_id(transaction_id)
            
            if not transaction or transaction.user_id != user_id:
                await query.edit_message_text(TRANSACTION_NOT_FOUND_MESSAGE, parse_mode="HTML")
                return
            
            # Get account name for display
            account = await self.account_service.get_account_by_id(transaction.account_id, user_id)
            account_name = account.name if account else f"Account {transaction.account_id}"
            
            # Store ALL editing state including original values
            if user_id not in self.user_data:
                self.user_data[user_id] = {}
            self.user_data[user_id].update({
                'editing_transaction_id': transaction_id,
                'original_account_id': transaction.account_id,
                'original_type': transaction.type,
                'original_category': transaction.category,
                'account_id': transaction.account_id,  # current selected during edit
                'type': transaction.type,              # current selected during edit  
                'category': transaction.category,      # current selected during edit
                'state': 'EDITING_TRANSACTION'
            })
            
            # Show account selection with calculated balances
            accounts = await self.account_service.get_user_accounts(user_id)
            keyboard = await create_account_keyboard_with_balances(accounts, user_id, self.account_service)
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Create a formatted transaction display with account name instead of ID
            transaction_display = (
                f"ID: {transaction.id}\n"
                f"Amount: {format_amount(transaction.amount)}\n"
                f"Type: {transaction.type}\n"
                f"Category: {transaction.category}\n"
                f"Account: {account_name}\n"
                f"Date: {transaction.created_at.strftime('%Y-%m-%d %H:%M:%S')}"
            )
            
            await query.edit_message_text(
                text=f"{EDIT_TRANSACTION_MESSAGE}\n<pre>{transaction_display}</pre>\n\n{ACCOUNT_SELECTION_MESSAGE}",
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
        
        
        elif query.data.startswith('delete_'):
            transaction_id = int(query.data.split('_')[1])
            await self.delete_transaction(update, context, transaction_id)


        
        elif query.data == 'type_income':
            # Ensure user has categories, creating defaults if needed
            income_cats, _ = await self.category_service.ensure_user_has_categories(user_id)
            user_income_categories = [cat.name for cat in income_cats]
            
            keyboard = create_category_keyboard(user_income_categories, 'income')
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
            
            keyboard = create_category_keyboard(user_expense_categories, 'expense')
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
        
        if query.data and (query.data.startswith('income_') or query.data.startswith('expense_')):
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
                keyboard = get_period_navigation_keyboard(period_type, 0, user_id)
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
                    transaction_id = self.user_data[user_id]['editing_transaction_id']
                    updated_transaction = await self.transaction_service.update_transaction(
                        transaction_id=transaction_id,
                        user_id=user_id,
                        amount=amount,
                        category=self.user_data[user_id]['category'],
                        transaction_type=self.user_data[user_id]['type'],
                        account_id=self.user_data[user_id]['account_id']
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
        # self.application.add_handler(CommandHandler('start', self.start))
        self.application.add_handler(CommandHandler('add_account', self.add_account))
        
        # Register callback query handler
        # self.application.add_handler(CallbackQueryHandler(self.button_handler))
        
        # Register message handler
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_amount))

        self.application.add_handler(ConversationHandler(
            entry_points=[CommandHandler('start', self.start)],
            states={
                MAIN_SCREEN: [
                    CallbackQueryHandler(self.account_selection_screen, pattern='^enter_transaction$'),
                    CallbackQueryHandler(self.transaction_view_screen, pattern='^view_transaction_'),
                    CallbackQueryHandler(self.show_period_selection, pattern='^select_period$'),
                ],
                ACCOUNT_SELECTION_SCREEN: [
                    CallbackQueryHandler(self.transaction_type_selection_screen, pattern='^account_'),
                    CallbackQueryHandler(self.back_handler, pattern='^back$')
                ],
                TRANSACTION_TYPE_SELECTION_SCREEN: [
                    CallbackQueryHandler(self.category_selection_screen, pattern='^type_'),
                    CallbackQueryHandler(self.back_handler, pattern='^back$')
                ],
                CATEGORY_SELECTION_SCREEN: [
                    CallbackQueryHandler(self.money_input_screen, pattern='^income_|expense_'),
                    CallbackQueryHandler(self.back_handler, pattern='^back$')
                ],
                TRANSACTION_VIEW_SCREEN: [
                    CallbackQueryHandler(self.account_selection_screen, pattern='^edit_transaction_'),
                    CallbackQueryHandler(self.back_handler, pattern='^back$')
                ]
            },
            fallbacks=[CommandHandler('start', self.start)]
        ))


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
