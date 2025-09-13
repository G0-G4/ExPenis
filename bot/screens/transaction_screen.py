
from telegram import Update
from telegram.ext import Application, ContextTypes, MessageHandler, filters
from decimal import Decimal, InvalidOperation

from bot.components.account_selector import AccountSelector
from bot.components.category_selector import CategorySelector
from bot.components.input import Input
from bot.bot_config import *
from bot.screens.check_box import Screen
from bot.messages import *
from core.service.transaction_service import create_transaction
from core.service.account_service import update_account_balance

class TransactionEdit(Screen):

    def __init__(self, application: Application):
        super().__init__()
        self.application = application
        self.user_id = None
        self.account_selector = AccountSelector(on_change=self.on_selection_change)
        self.category_selector = CategorySelector(on_change=self.on_selection_change)
        self.amount_input = Input(on_input=self.on_amount_input)
        self.message = "Please select both account and category first"
        self.ready_for_input = False

        application.add_handler(CallbackQueryHandler(
            self.handle_user_presses,
            pattern='^cb_|^back$|^enter_transaction$'
        ))
        application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.amount_input.handle_message)
        )

    async def on_selection_change(self, component):
        self.ready_for_input = (
            self.account_selector.account_id is not None and 
            self.category_selector.category is not None
        )
        if self.ready_for_input:
            self.message = TRANSACTION_INPUT_PROMPT
        else:
            self.message = "Please select both account and category first"

    async def handle_user_presses(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        user_id = query.from_user.id
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

    async def on_amount_input(self, amount: str):
        try:
            amount_decimal = Decimal(amount)
            if amount_decimal <= 0:
                raise ValueError("Amount must be positive")

            transaction = await create_transaction(
                user_id=self.user_id,
                amount=float(amount_decimal),
                category=self.category_selector.category,
                transaction_type=self.category_selector.transaction_type,
                account_id=self.account_selector.account_id
            )

            account = self.account_selector.selected_account
            new_balance = float(Decimal(str(account.balance)) + 
                (amount_decimal if self.category_selector.transaction_type == 'income' else -amount_decimal))
            await update_account_balance(account.id, self.user_id, new_balance)

            await self.application.bot.send_message(
                chat_id=self.user_id,
                text=TRANSACTION_RECORDED_MESSAGE
            )

            self.amount_input.value = None
            await self.account_selector.init(self.user_id)
            await self.category_selector.init(self.user_id, None)
            self.ready_for_input = False

        except InvalidOperation:
            await self.application.bot.send_message(
                chat_id=self.user_id,
                text=INVALID_AMOUNT_MESSAGE
            )
        except Exception as e:
            logger.error(f"Error creating transaction: {e}")
            await self.application.bot.send_message(
                chat_id=self.user_id,
                text=ERROR_SAVING_TRANSACTION_MESSAGE
            )

