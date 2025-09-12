from telegram import Update
from datetime import date

from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ConversationHandler, Application
from core.helpers import format_percentage, get_target_date
from bot.messages import *
from bot.bot_config import *
from bot.keyboards import  *
from core.service.transaction_service import get_custom_period_statistics
class Screen:

    def __init__(self, application: Application):
        self.update = None
        self.text = "тестовый экран"
        application.add_handler(CallbackQueryHandler(self.button_handler, pattern='^button$'))

    def get_mark(self):
        return InlineKeyboardMarkup([[InlineKeyboardButton(self.text, callback_data="button")]])
    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        print("button pressed")
        self.text+="+"
        await self.display_on(update)


    async def display_on(self, update):
        if update.message:
            await update.message.reply_text(self.text, reply_markup=self.get_mark(), parse_mode="HTML")
        elif update.callback_query:
            await update.callback_query.edit_message_text(text=self.text, reply_markup=self.get_mark(), parse_mode="HTML")
    async def set_display(self, update):
        self.update = update