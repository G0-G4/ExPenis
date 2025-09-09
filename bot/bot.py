from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters

from core.config import TOKEN
import logging

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Define conversation states
ENTER_TRANSACTION, SELECT_TYPE, SELECT_CATEGORY, ENTER_AMOUNT = range(4)

# Define income and expense categories
INCOME_CATEGORIES = ['Salary', 'Freelance', 'Investment', 'Gift', 'Other Income']
EXPENSE_CATEGORIES = ['Food', 'Transport', 'Entertainment', 'Shopping', 'Bills', 'Rent', 'Other Expense']

# Temporary storage for transactions (in a real app, this would be a database)
user_data = {}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message and show main menu"""
    keyboard = [
        [InlineKeyboardButton("Enter Transaction", callback_data='enter_transaction')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.message:
        await update.message.reply_text(
            "Welcome to Expense Tracker Bot! Click the button below to enter a transaction.",
            reply_markup=reply_markup
        )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
            text="Select transaction type:",
            reply_markup=reply_markup
        )
    
    elif query.data == 'type_income':
        # Show income categories in 3 columns
        keyboard = []
        row = []
        for i, category in enumerate(INCOME_CATEGORIES):
            row.append(InlineKeyboardButton(category, callback_data=f'income_{i}'))
            if len(row) == 3 or i == len(INCOME_CATEGORIES) - 1:
                keyboard.append(row)
                row = []
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            text="Select income category:",
            reply_markup=reply_markup
        )
        
        # Store transaction type for this user
        if user_id not in user_data:
            user_data[user_id] = {}
        user_data[user_id]['type'] = 'income'
    
    elif query.data == 'type_expense':
        # Show expense categories in 3 columns
        keyboard = []
        row = []
        for i, category in enumerate(EXPENSE_CATEGORIES):
            row.append(InlineKeyboardButton(category, callback_data=f'expense_{i}'))
            if len(row) == 3 or i == len(EXPENSE_CATEGORIES) - 1:
                keyboard.append(row)
                row = []
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            text="Select expense category:",
            reply_markup=reply_markup
        )
        
        # Store transaction type for this user
        if user_id not in user_data:
            user_data[user_id] = {}
        user_data[user_id]['type'] = 'expense'
    
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
            user_data[user_id]['category'] = category
            
            await query.edit_message_text(
                text=f"Selected category: {category}\n\nPlease enter the amount:"
            )
            
            # Set state to expect amount input
            user_data[user_id]['state'] = ENTER_AMOUNT


async def handle_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle amount input from user"""
    if not update.message or not update.message.from_user:
        return
        
    user_id = update.message.from_user.id
    
    # Check if we're expecting an amount input
    if user_id in user_data and user_data[user_id].get('state') == ENTER_AMOUNT:
        try:
            amount_text = update.message.text
            if not amount_text:
                await update.message.reply_text("Please enter a valid number for the amount.")
                return
                
            amount = float(amount_text)
            
            # Get transaction details
            transaction_type = user_data[user_id]['type']
            category = user_data[user_id]['category']
            
            # Format transaction for display
            if transaction_type == 'income':
                transaction_text = f"✅ Income: +{amount} ({category})"
            else:
                transaction_text = f"❌ Expense: -{amount} ({category})"
            
            # In a real app, you would save this to a database
            # For now, we'll just display it
            await update.message.reply_text(
                f"Transaction recorded:\n{transaction_text}\n\nThank you!"
            )
            
            # Clear user data for this transaction
            user_data[user_id] = {}
            
            # Show main menu again
            keyboard = [
                [InlineKeyboardButton("Enter Transaction", callback_data='enter_transaction')],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "What would you like to do next?",
                reply_markup=reply_markup
            )
            
        except ValueError:
            await update.message.reply_text("Please enter a valid number for the amount.")
    else:
        # If not in amount input state, show main menu
        keyboard = [
            [InlineKeyboardButton("Enter Transaction", callback_data='enter_transaction')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "Welcome to Expense Tracker Bot! Click the button below to enter a transaction.",
            reply_markup=reply_markup
        )


def main():
    """Run the bot."""
    # Create the Application and pass it your bot's token.
    if not TOKEN:
        logger.error("TOKEN is not set. Please check your .env file.")
        return
        
    application = ApplicationBuilder().token(TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_amount))

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()