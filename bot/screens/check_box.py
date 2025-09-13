from typing import List
import inspect
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import BadRequest

from bot.bot_config import *
from bot.components.panel import Panel


class Screen:

    def __init__(self, message: str = ""):
        self.panel = Panel()
        self.initiated = False
        self.message = message

    async def handle_user_presses(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        raise NotImplementedError

    async def display_on(self, update: Update, text: str, markup):
        """Display the panel on the given update"""
        try:
            if update.message:
                await update.message.reply_text(
                    text=text,
                    reply_markup=InlineKeyboardMarkup(markup.render()),
                    parse_mode="HTML"
                )
            elif update.callback_query:
                await update.callback_query.edit_message_text(
                    text=text,
                    reply_markup=InlineKeyboardMarkup(markup.render()),
                    parse_mode="HTML"
                )
        except BadRequest as e:
            print(f"No modifications needed: {e.message}")
