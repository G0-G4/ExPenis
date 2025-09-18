
from telegram.ext import ApplicationBuilder
from telegram import BotCommand, Update

from bot.screens.unified_main_screen import UnifiedMainScreen
from core.config import TOKEN
from core.service.account_service import AccountService
from telegram.ext import ContextTypes
import logging

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", 
    level=logging.INFO
)
logger = logging.getLogger(__name__)
# Reduce noise from these libraries
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('httpcore').setLevel(logging.WARNING)



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
        unified_main_screen = UnifiedMainScreen(self.application)

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
