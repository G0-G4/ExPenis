from cmath import acosh
from os import supports_effective_ids

from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ConversationHandler, Application

from bot.screens.main_screen import MainScreen
from bot.screens.money_input import MONEY_INPUT_SCREEN, money_input_handler, money_input_screen
from bot.screens.periods import PERIOD_SELECTION_SCREEN, PERIOD_VIEW_SCREEN, custom_period, period_view_screen, \
    period_selection_screen
from bot.screens.transaction_screen import AccountSelector, CategorySelector, TransactionEdit

from core.helpers import format_percentage
from bot.messages import *
from bot.bot_config import *
from bot.keyboards import  *
from core.config import TOKEN
from core.service.transaction_service import create_transaction, delete_transaction, get_custom_period_statistics, \
    get_transaction_by_id, \
    update_transaction
from core.service.category_service import get_user_expense_categories, get_user_income_categories
from core.service.account_service import AccountService, get_account_by_id, get_user_accounts
import logging

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)
logging.getLogger('sqlalchemy.engine').setLevel(logging.ERROR)



class ExpenseBot:
    def __init__(self):
        self.user_data = {}
        self.account_service = AccountService()
        self.application = None


    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle all button presses"""
        query = update.callback_query
        
        if not query or not query.from_user:
            return
            
        await query.answer()

    async def set_bot_commands(self):
        """Set bot commands menu"""
        commands = [
            BotCommand("start", "Open the main menu"),
            BotCommand("add_account", "Create a new account"),
            BotCommand("main", "Open the main menu"),
        ]
        await self.application.bot.set_my_commands(commands)

    def _initialize_application(self):
        """Initialize the Telegram application and register handlers"""
        if not TOKEN:
            logger.error("TOKEN is not set. Please check your .env file.")
            return False

        self.application = ApplicationBuilder().token(TOKEN).build()
        # screen = Screen(application=self.application)
        main = MainScreen(self.application)
        # acs = AccountSelector(self.application)
        # acs = CategorySelector(self.application)
        te = TransactionEdit(self.application)
        # transaction_screen = TransactionEditScreen(self.application)

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
