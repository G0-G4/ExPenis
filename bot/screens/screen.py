from typing import List
import inspect
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import BadRequest

from bot.bot_config import *
from bot.components.component import UiComponent
from telegram.ext import ContextTypes
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
        if not self.initiated:
            await self.init(update, context)
        handled = await self.handle_callback(update, context, query.data)
        if not self.initiated or handled:
            await self.display_on(update, await self.get_message(update, context), self.render(update, context))

    async def handle_user_messages(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        message = update.message
        if not self.initiated:
            await self.init(update, context)
        handled = await self.handle_message(update, context, message)
        buttons_update = context.user_data['update'] or update
        if not self.initiated or handled:
            await self.display_on(buttons_update, await self.get_message(buttons_update, context), self.render(buttons_update, context))
        if handled:
            chat_id = update.effective_chat.id
            message_id_to_delete = update.message.id
            await context.bot.delete_message(chat_id=chat_id, message_id=message_id_to_delete)

    @abstractmethod
    def get_user_state(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        raise NotImplementedError

    # Note: init, clear_state are inherited from UiComponent
    # initiated is a property inherited from StatefulComponent

    @abstractmethod
    async def handle_message(self, update, context, message):
        raise NotImplementedError

    async def get_message(self, update, context):
        user_state = self.get_user_state(update, context)
        return user_state['message']