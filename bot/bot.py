from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters

from core.config import TOKEN
from core.service.transaction_service import TransactionService
import logging

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

# Define conversation states
ENTER_TRANSACTION, SELECT_TYPE, SELECT_CATEGORY, ENTER_AMOUNT = range(4)

# Define income and expense categories
INCOME_CATEGORIES = ['Salary', 'Freelance', 'Investment', 'Gift', 'Other Income']
EXPENSE_CATEGORIES = ['Food', 'Transport', 'Entertainment', 'Shopping', 'Bills', 'Rent', 'Other Expense']

# UI constants
CATEGORIES_PER_ROW = 3
WELCOME_MESSAGE = "Welcome to Expense Tracker Bot! Click the button below to enter a transaction."
TRANSACTION_TYPE_MESSAGE = "Select transaction type:"
INCOME_CATEGORY_MESSAGE = "Select income category:"
EXPENSE_CATEGORY_MESSAGE = "Select expense category:"
AMOUNT_PROMPT_MESSAGE = "Please enter the amount:"
INVALID_AMOUNT_MESSAGE = "Please enter a valid number for the amount."
THANK_YOU_MESSAGE = "Thank you!"
MAIN_MENU_MESSAGE = "What would you like to do next?"
VIEW_TRANSACTIONS_MESSAGE = "Here are your recent transactions:"


class ExpenseBot:
    def __init__(self):
        self.user_data = {}
        self.transaction_service = TransactionService()
        self.application = None

    def create_category_keyboard(self, categories, prefix):
        """Create a keyboard with categories arranged in columns"""
        keyboard = []
        row = []
        for i, category in enumerate(categories):
            row.append(InlineKeyboardButton(category, callback_data=f'{prefix}_{i}'))
            if len(row) == CATEGORIES_PER_ROW or i == len(categories) - 1:
                keyboard.append(row)
                row = []
        return keyboard

    def get_main_menu_keyboard(self):
        """Create the main menu keyboard"""
        return [[InlineKeyboardButton("Enter Transaction", callback_data='enter_transaction')]]

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send welcome message and show main menu"""
        keyboard = self.get_main_menu_keyboard()
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.message:
            await update.message.reply_text(
                WELCOME_MESSAGE,
                reply_markup=reply_markup
            )

    async def statistics(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send category summary statistics"""
        res = await self.transaction_service.get_category_summary(update.message.from_user.id)
        await update.message.reply_text(str(res))

    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle all button presses"""
        query = update.callback_query
        
        if not query or not query.from_user:
            return
            
        await query.answer()
        
        user_id = query.from_user.id
        
        if query.data == 'enter_transaction':
            # Show transaction type selection (+ or -)
            keyboard = [
                [
                    InlineKeyboardButton("Income (+)", callback_data='type_income'),
                    InlineKeyboardButton("Expense (-)", callback_data='type_expense'),
                ],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                text=TRANSACTION_TYPE_MESSAGE,
                reply_markup=reply_markup
            )
        
        elif query.data == 'type_income':
            # Show income categories
            keyboard = self.create_category_keyboard(INCOME_CATEGORIES, 'income')
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                text=INCOME_CATEGORY_MESSAGE,
                reply_markup=reply_markup
            )
            
            # Store transaction type for this user
            if user_id not in self.user_data:
                self.user_data[user_id] = {}
            self.user_data[user_id]['type'] = 'income'
        
        elif query.data == 'type_expense':
            # Show expense categories
            keyboard = self.create_category_keyboard(EXPENSE_CATEGORIES, 'expense')
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                text=EXPENSE_CATEGORY_MESSAGE,
                reply_markup=reply_markup
            )
            
            # Store transaction type for this user
            if user_id not in self.user_data:
                self.user_data[user_id] = {}
            self.user_data[user_id]['type'] = 'expense'
        
        elif query.data and (query.data.startswith('income_') or query.data.startswith('expense_')):
            # Category selected, ask for amount
            if query.data:
                category_type, category_index = query.data.split('_')
                category_index = int(category_index)
                
                if category_type == 'income':
                    category = INCOME_CATEGORIES[category_index]
                else:
                    category = EXPENSE_CATEGORIES[category_index]
                
                # Store selected category
                self.user_data[user_id]['category'] = category
                
                await query.edit_message_text(
                    text=f"Selected category: {category}\n\n{AMOUNT_PROMPT_MESSAGE}"
                )
                
                # Set state to expect amount input
                self.user_data[user_id]['state'] = ENTER_AMOUNT

    async def handle_amount(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle amount input from user"""
        if not update.message or not update.message.from_user:
            return
            
        user_id = update.message.from_user.id
        
        # Check if we're expecting an amount input
        if user_id in self.user_data and self.user_data[user_id].get('state') == ENTER_AMOUNT:
            try:
                amount_text = update.message.text
                if not amount_text:
                    await update.message.reply_text(INVALID_AMOUNT_MESSAGE)
                    return
                    
                amount = float(amount_text)
                
                # Get transaction details
                transaction_type = self.user_data[user_id]['type']
                category = self.user_data[user_id]['category']
                
                # Format transaction for display
                if transaction_type == 'income':
                    transaction_text = f"✅ Income: +{amount} ({category})"
                else:
                    transaction_text = f"❌ Expense: -{amount} ({category})"
                
                # Save transaction to database using transaction service
                try:
                    transaction = await self.transaction_service.create_transaction(
                        user_id=user_id,
                        amount=amount,
                        category=category,
                        transaction_type=transaction_type,
                    )
                    
                    await update.message.reply_text(
                        f"Transaction recorded:\n{transaction_text}\n\nTransaction ID: {transaction.id}\n\n{THANK_YOU_MESSAGE}"
                    )
                except Exception as e:
                    logger.error(f"Error saving transaction: {e}")
                    await update.message.reply_text(
                        f"Transaction recorded:\n{transaction_text}\n\nNote: Failed to save to database.\n\n{THANK_YOU_MESSAGE}"
                    )
                
                # Clear user data for this transaction
                self.user_data[user_id] = {}
                
                # Show main menu again
                keyboard = self.get_main_menu_keyboard()
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    MAIN_MENU_MESSAGE,
                    reply_markup=reply_markup
                )
                
            except ValueError:
                await update.message.reply_text(INVALID_AMOUNT_MESSAGE)
        else:
            # If not in amount input state, show main menu
            keyboard = self.get_main_menu_keyboard()
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                WELCOME_MESSAGE,
                reply_markup=reply_markup
            )

    def _initialize_application(self):
        """Initialize the Telegram application and register handlers"""
        if not TOKEN:
            logger.error("TOKEN is not set. Please check your .env file.")
            return False
            
        self.application = ApplicationBuilder().token(TOKEN).build()
        
        # Register command handlers
        self.application.add_handler(CommandHandler('start', self.start))
        self.application.add_handler(CommandHandler('stat', self.statistics))
        
        # Register callback query handler
        self.application.add_handler(CallbackQueryHandler(self.button_handler))
        
        # Register message handler
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_amount))
        
        return True

    def run(self):
        """Run the bot"""
        if not self._initialize_application():
            return
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)


def main():
    """Run the bot."""
    bot = ExpenseBot()
    bot.run()


if __name__ == '__main__':
    main()
