from cmath import acosh
from os import supports_effective_ids

from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ConversationHandler

from bot.screens.account_selection import ACCOUNT_SELECTION_SCREEN, account_selection_screen
from bot.screens.add_acount import ACCOUNT_NAME, ADD_ACCOUNT_SCREEN, account_name, add_account, create_account_handler
from bot.screens.category_selection import CATEGORY_SELECTION_SCREEN, category_selection_screen
from bot.screens.main import MAIN_SCREEN, start
from bot.screens.money_input import MONEY_INPUT_SCREEN, money_input_handler, money_input_screen
from bot.screens.transaction_type_selection import TRANSACTION_TYPE_SELECTION_SCREEN, transaction_type_selection_screen
from bot.screens.transaction_view import TRANSACTION_VIEW_SCREEN, delete_transaction_handler, transaction_view_screen
from core.helpers import format_percentage
from bot.messages import *
from bot.bot_config import *
from bot.keyboards import  *
from core.config import TOKEN
from core.service.transaction_service import create_transaction, delete_transaction, get_transaction_by_id, \
    update_transaction
from core.service.category_service import get_user_expense_categories, get_user_income_categories
from core.service.account_service import AccountService, get_account_by_id, get_user_accounts
import logging

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)
logging.getLogger('sqlalchemy.engine').setLevel(logging.ERROR)

ACCOUNT_SELECTION, SELECT_TYPE, SELECT_CATEGORY, ENTER_AMOUNT, SELECT_PERIOD, VIEW_PERIOD, ENTER_ACCOUNT_NAME, ENTER_ACCOUNT_AMOUNT, = range(
    8)





class ExpenseBot:
    def __init__(self):
        self.user_data = {}
        self.account_service = AccountService()
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
        period_data = await get_period_statistics(
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
        categories = await get_user_income_categories(user_id)
        return [cat.name for cat in categories] if categories else []

    async def get_user_expense_categories(self, user_id: int) -> list:
        """Get expense category names for a user"""
        categories = await get_user_expense_categories(user_id)
        return [cat.name for cat in categories] if categories else []





    async def refresh_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Refresh the main menu view"""
        await start(update, context)





    async def back_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()

        # Get previous state from user_data
        previous_state = get_previous_state(context)
        context.user_data['set_previous'] = False

        # Handle going back to previous state
        if previous_state == MAIN_SCREEN:
            return await start(update, context)
        if previous_state == ACCOUNT_SELECTION_SCREEN:
            return await account_selection_screen(update, context)
        elif previous_state == TRANSACTION_TYPE_SELECTION_SCREEN:
            return await transaction_type_selection_screen(update, context)
        elif previous_state == CATEGORY_SELECTION_SCREEN:
            return await category_selection_screen(update, context)
        elif previous_state == TRANSACTION_VIEW_SCREEN:
            return await transaction_view_screen(update, context)
        elif previous_state == ADD_ACCOUNT_SCREEN:
            return await add_account(update, context)
        elif previous_state == ACCOUNT_NAME:
            return await account_name(update, context)

        return previous_state



    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle all button presses"""
        query = update.callback_query
        
        if not query or not query.from_user:
            return
            
        await query.answer()


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
            await transaction_view_screen(update, context)
        
        elif query.data.startswith('edit_full_'):
            transaction_id = int(query.data.split('_')[2])
            
            # Get transaction details
            transaction = await get_transaction_by_id(transaction_id)
            
            if not transaction or transaction.user_id != user_id:
                await query.edit_message_text(TRANSACTION_NOT_FOUND_MESSAGE, parse_mode="HTML")
                return
            
            # Get account name for display
            account = await get_account_by_id(transaction.account_id, user_id)
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
            accounts = await get_user_accounts(user_id)
            keyboard = await create_account_keyboard_with_balances(accounts, user_id)
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
        
        



        
        elif query.data == 'type_income':
            # Ensure user has categories, creating defaults if needed
            income_cats, _ = await ensure_user_has_categories(user_id)
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
            _, expense_cats = await ensure_user_has_categories(user_id)
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
            

        
        # Handle account amount input

        
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
                period_data = await get_custom_period_statistics(
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
        
        # self.application.add_handler(CommandHandler('add_account', add_account))
        
        # Register callback query handler
        # self.application.add_handler(CallbackQueryHandler(self.button_handler))
        
        # Register message handler
        # self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_amount))

        self.application.add_handler(ConversationHandler(
            entry_points=[CommandHandler('start', start), CommandHandler('add_account', add_account)],
            states={
                MAIN_SCREEN: [
                    CallbackQueryHandler(account_selection_screen, pattern='^enter_transaction$'),
                    CallbackQueryHandler(transaction_view_screen, pattern='^view_transaction_'),
                    CallbackQueryHandler(self.show_period_selection, pattern='^select_period$'),
                ],
                ACCOUNT_SELECTION_SCREEN: [
                    CallbackQueryHandler(transaction_type_selection_screen, pattern='^account_'),
                    CallbackQueryHandler(self.back_handler, pattern='^back')
                ],
                TRANSACTION_TYPE_SELECTION_SCREEN: [
                    CallbackQueryHandler(category_selection_screen, pattern='^type_'),
                    CallbackQueryHandler(self.back_handler, pattern='^back')
                ],
                CATEGORY_SELECTION_SCREEN: [
                    CallbackQueryHandler(money_input_screen, pattern='^income_|expense_'),
                    CallbackQueryHandler(self.back_handler, pattern='^back')
                ],
                MONEY_INPUT_SCREEN: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, money_input_handler),
                    CallbackQueryHandler(self.back_handler, pattern='^back')
                ],
                TRANSACTION_VIEW_SCREEN: [
                    CallbackQueryHandler(account_selection_screen, pattern='^edit_transaction_'),
                    CallbackQueryHandler(delete_transaction_handler, pattern='^delete_'),
                    CallbackQueryHandler(self.back_handler, pattern='^back')
                ],
                ADD_ACCOUNT_SCREEN: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, account_name),
                    CallbackQueryHandler(self.back_handler, pattern='^back')
                ],
                ACCOUNT_NAME: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, create_account_handler),
                    CallbackQueryHandler(self.back_handler, pattern='^back')
                ]

            },
            fallbacks=[CommandHandler('start', start)]
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
