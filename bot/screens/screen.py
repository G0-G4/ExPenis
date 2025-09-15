from typing import List
import inspect
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import BadRequest

from bot.bot_config import *
from bot.components.component import UiComponent
from abc import abstractmethod
from bot.components.panel import Panel


class Screen(UiComponent):

    def __init__(self):
        super().__init__()

    async def display_on(self, update: Update, text: str, keyboard_markup):
        try:
            if update.message:
                await update.message.reply_text(
                    text=text,
                    reply_markup=InlineKeyboardMarkup(keyboard_markup),
                    parse_mode="HTML"
                )
            elif update.callback_query:
                await update.callback_query.edit_message_text(
                    text=text,
                    reply_markup=InlineKeyboardMarkup(keyboard_markup),
                    parse_mode="HTML"
                )
        except BadRequest as e:
            print(f"No modifications needed: {e.message}")

    async def handle_user_presses(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        initiated = await self.initiated(update, context)
        if not initiated:
            await self.init(update, context)
        handled = await self.handle_callback(update, context, query.data)
        if not initiated or handled:
            await self.display_on(update, await self.get_message(update, context), self.render(update, context))

    async def handle_user_messages(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        message = update.message
        initiated = await self.initiated(update, context)
        handled = await self.handle_message(update, context, message)
        if not initiated or handled:
            await self.display_on(context.user_data['update'] or update, await self.get_message(update, context), self.render(update, context))

    @abstractmethod
    def get_user_state(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        raise NotImplementedError

    @abstractmethod
    async def initiated(self, update, context): # TODO change to typed state. store in object not dict
        raise NotImplementedError

    @abstractmethod
    async def init(self, update, context):
        raise NotImplementedError

    @abstractmethod
    async def handle_message(self, update, context, message):
        raise NotImplementedError

    async def get_message(self, update, context):
        user_state = self.get_user_state(update, context)
        return user_state['message']