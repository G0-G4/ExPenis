
from telegram import Update, InlineKeyboardMarkup
from telegram.ext import Application
from telegram.error import BadRequest
from decimal import Decimal

from bot.components.account_selector import AccountSelector
from bot.components.category_selector import CategorySelector
from bot.components.input import Input
from bot.bot_config import *
from bot.messages import *
from bot.screens.screen import Screen
from core.service.transaction_service import create_transaction

class TransactionEdit(Screen):

    def __init__(self, application: Application):
        super().__init__()
        self.application = application
        self.press_handler = CallbackQueryHandler(
            self.handle_user_presses,
            pattern='^cb_|^back$|^enter_transaction$'
        )
        self.input_handler = MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_user_messages)
        application.add_handler(self.press_handler)
        application.add_handler(self.input_handler)

    def get_user_state(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Get or create user-specific transaction edit state"""
        if 'update' not in context.user_data and update.callback_query is not None:
            context.user_data['update'] = update
        context.user_data['user_id'] = context._user_id
        if 'transaction_edit' not in context.user_data:
            context.user_data['transaction_edit'] = {
                'account_selector': AccountSelector(on_change=self.on_selection_change),
                'category_selector': CategorySelector(on_change=self.on_selection_change),
                'amount_input': Input(on_change=self.on_amount_input),
                'message': "Please select both account and category first",
                'ready_for_input': False,
                'account': None,
                'category': None
            }
        return context.user_data['transaction_edit']

    async def on_selection_change(self, component, update, context):
        user_state = self.get_user_state(update, context)
        account_selector = user_state['account_selector']
        category_selector = user_state['category_selector']
        user_state['ready_for_input'] = (
                account_selector.account_id is not None and
                category_selector.category is not None
        )

        if user_state['ready_for_input']:
            user_state['message'] = TRANSACTION_INPUT_PROMPT
            user_state['amount_input'].activate()
        else:
            user_state['message'] = "Please select both account and category first"

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message):
        """Handle amount input messages"""
        user_state = self.get_user_state(update, context)
        amount_input = user_state['amount_input']
        
        if amount_input.is_active():
            return await amount_input.handle_message(update, context, message)
        return False

    async def initiated(self, update, context): # TODO change to typed state. store in object not dict
        user_state = self.get_user_state(update, context)
        account_selector = user_state['account_selector']
        category_selector = user_state['category_selector']
        return account_selector.initiated and category_selector.initiated

    async def init(self, update, context):
        user_state = self.get_user_state(update, context)
        account_selector = user_state['account_selector']
        category_selector = user_state['category_selector']
        if not account_selector.initiated:
            await account_selector.init(context.user_data['user_id'])
        if not category_selector.initiated:
            await category_selector.init(context.user_data['user_id'], update)
    async def handle_callback(self, update, context, query_data: str):
        user_state = self.get_user_state(update, context)
        account_selector = user_state['account_selector']
        category_selector = user_state['category_selector']
        handle_account = await account_selector.handle_callback(update, context, query_data)
        handle_category = await category_selector.handle_callback(update, context, query_data)
        return handle_account or handle_category

    def render(self, update, context):
        user_state = self.get_user_state(update, context)
        account_selector = user_state['account_selector']
        category_selector = user_state['category_selector']
        return account_selector.render(update, context) + category_selector.render(update, context)
    

    async def on_amount_input(self, input: Input, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.message.from_user.id
        user_state = self.get_user_state(update, context)

        amount_decimal = Decimal(input.value)
        if amount_decimal <= 0:
            raise ValueError("Amount must be positive")

        account_selector = user_state['account_selector']
        category_selector = user_state['category_selector']

        await create_transaction(
            user_id=user_id,
            amount=float(amount_decimal),
            category=category_selector.category,
            transaction_type=category_selector.transaction_type,
            account_id=account_selector.account_id
        )

        chat_id = update.effective_chat.id
        message_id_to_delete = update.message.id
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id_to_delete)

        # Reset the user state for a new transaction
        buttons_update = context.user_data['update'] # TODO to base class
        del context.user_data['transaction_edit']
        await self.init(buttons_update, context)
        await self.display_on(buttons_update, await self.get_message(update, context), self.render(update, context))

