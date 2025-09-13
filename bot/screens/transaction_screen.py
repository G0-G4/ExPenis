
from telegram import Update
from telegram.ext import Application
from decimal import Decimal

from bot.components.account_selector import AccountSelector
from bot.components.category_selector import CategorySelector
from bot.components.input import Input
from bot.bot_config import *
from bot.screens.check_box import Screen
from bot.messages import *
from core.service.transaction_service import create_transaction

class TransactionEdit(Screen):

    def __init__(self, application: Application):
        super().__init__()
        self.application = application
        self.clear()
        self.press_handler = CallbackQueryHandler(
            self.handle_user_presses,
            pattern='^cb_|^back$|^enter_transaction$'
        )
        self.input_handler = MessageHandler(filters.TEXT & ~filters.COMMAND, self.amount_input.handle_message)
        application.add_handler(self.press_handler)
        application.add_handler(self.input_handler)

    def clear(self):
        if hasattr(self, "input_handler"):
            self.application.remove_handler(self.input_handler)
        if hasattr(self, "press_handler"):
            self.application.remove_handler(self.press_handler)
        self.user_id = None
        self.account_selector = AccountSelector(on_change=self.on_selection_change)
        self.category_selector = CategorySelector(on_change=self.on_selection_change)
        self.amount_input = Input(on_input=self.on_amount_input)
        self.update = None
        self.user_id = None
        self.message = "Please select both account and category first"
        self.ready_for_input = False

    async def on_selection_change(self, component):
        self.ready_for_input = (
            self.account_selector.account_id is not None and 
            self.category_selector.category is not None
        )
        if self.ready_for_input:
            self.message = TRANSACTION_INPUT_PROMPT
            self.amount_input.activate()
        else:
            self.message = "Please select both account and category first"

    async def handle_user_presses(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        user_id = query.from_user.id
        self.update = update
        self.user_id = user_id
        initiated = self.account_selector.initiated and self.category_selector.initiated
        if not self.account_selector.initiated:
            await self.account_selector.init(user_id)
        if not self.category_selector.initiated:
            await self.category_selector.init(user_id, update)
        handle_account = await self.account_selector.handle_callback(query.data)
        handle_category = await self.category_selector.handle_callback(query.data)
        if not initiated or handle_account or handle_category:
            await self.display_on(
                update,
                self.message,
                self
            )

    def render(self):
        return self.account_selector.render() + self.category_selector.render()

    async def on_amount_input(self, input: Input, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            user_id = update.message.from_user.id
            amount_decimal = Decimal(input.value)
            if amount_decimal <= 0:
                raise ValueError("Amount must be positive")

            transaction = await create_transaction(
                user_id=self.user_id,
                amount=float(amount_decimal),
                category=self.category_selector.category,
                transaction_type=self.category_selector.transaction_type,
                account_id=self.account_selector.account_id
            )

            chat_id = update.effective_chat.id
            message_id_to_delete = update.message.id
            await context.bot.delete_message(chat_id=chat_id, message_id=message_id_to_delete)


            user_id = self.user_id
            update = self.update
            self.__init__(self.application)
            await self.account_selector.init(user_id)
            await self.category_selector.init(user_id, update)
            await self.display_on(update, self.message, self)


        except Exception as e:
            print("errror " + str(e))
