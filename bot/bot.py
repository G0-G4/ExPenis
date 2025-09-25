import sys

from telegram.ext import ApplicationBuilder
from telegram import BotCommand, Update

from bot.screens.unified_main_screen import UnifiedMainScreen
from core.config import TOKEN
from core.service.account_service import AccountService
from telegram.ext import ContextTypes
import logging
import logging.handlers

log_filename = f"logs/expenis.log"

root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(filename)s - %(lineno)d - %(message)s')

# File handler
file_handler = logging.handlers.RotatingFileHandler(
    log_filename,
    backupCount=3,
    maxBytes=5_000_000
)
file_handler.setFormatter(formatter)

# Console handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(formatter)

root_logger.handlers = []
root_logger.addHandler(file_handler)
root_logger.addHandler(console_handler)

logger = logging.getLogger(__name__)
# Silence noisy libraries
logging.getLogger('sqlalchemy.engine').setLevel(logging.ERROR)  # Only show SQL errors
logging.getLogger('sqlalchemy.pool').setLevel(logging.ERROR)
logging.getLogger('httpx').setLevel(logging.ERROR)
logging.getLogger('httpcore').setLevel(logging.ERROR)
logging.getLogger('telegram').setLevel(logging.WARNING)  # Reduce telegram verbosity
logging.getLogger('asyncio').setLevel(logging.WARNING)
logging.getLogger('aiosqlite').setLevel(logging.WARNING)



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
            BotCommand("accounts", "Create or edit accounts"),
            BotCommand("stats", "View stats"),
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
