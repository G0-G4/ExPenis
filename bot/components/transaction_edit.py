from telegram import Update
from telegram.ext import ContextTypes
from decimal import Decimal

from bot.components.component import UiComponent
from bot.components.account_selector import AccountSelector
from bot.components.category_selector import CategorySelector
from bot.components.input import Input
from bot.messages import *
from core.service.transaction_service import create_transaction, get_transaction_by_id, update_transaction


class TransactionEdit(UiComponent):
    def __init__(self, component_id: str = None, on_change: callable = None):
        super().__init__(component_id, on_change)
        self.account_selector = AccountSelector(on_change=self.on_selection_change)
        self.category_selector = CategorySelector(on_change=self.on_selection_change)
        self.amount_input = Input(on_change=self.on_amount_input)
        self.message = "Please select both account and category first"
        self.ready_for_input = False
        self.initiated = False
        self.transaction_id = None  # For editing existing transactions

    async def init(self, user_id: int, update=None, transaction_id: int = None):
        """Initialize component, optionally with existing transaction data"""
        self.transaction_id = transaction_id

        if transaction_id:
            # Load existing transaction data and populate selectors
            transaction = await get_transaction_by_id(transaction_id)
            if transaction:
                # Set values BEFORE initializing selectors so checkboxes show correctly
                self.account_selector.account_id = transaction.account_id
                self.category_selector.category = transaction.category
                self.category_selector.transaction_type = transaction.type
                
                # Initialize selectors with the pre-set values
                await self.account_selector.init(user_id)
                await self.category_selector.init(user_id, update, transaction.type)
                
                # Set ready for input and activate amount input since both selectors have values
                self.ready_for_input = True
                self.message = f"Editing transaction: {transaction.amount} - Enter new amount or keep current"
                self.amount_input.activate()
        else:
            # Initialize selectors for new transaction
            if not self.account_selector.initiated:
                await self.account_selector.init(user_id)
            if not self.category_selector.initiated:
                await self.category_selector.init(user_id, update)
            

        self.initiated = True

    def clear_state(self):
        """Reset component state"""
        self.account_selector = AccountSelector(on_change=self.on_selection_change)
        self.category_selector = CategorySelector(on_change=self.on_selection_change)
        self.amount_input = Input(on_change=self.on_amount_input)
        self.message = "Please select both account and category first"
        self.ready_for_input = False
        self.initiated = False
        self.transaction_id = None

    async def on_selection_change(self, component, update, context):
        """Handle account/category selection changes"""
        self.ready_for_input = (
            self.account_selector.account_id is not None and
            self.category_selector.category is not None
        )

        if self.ready_for_input:
            self.message = TRANSACTION_INPUT_PROMPT
            self.amount_input.activate()
        else:
            self.message = "Please select both account and category first"

    async def on_amount_input(self, inp: Input, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle amount input and create/update transaction"""
        user_id = update.message.from_user.id

        try:
            amount_decimal = Decimal(inp.value)
            if amount_decimal <= 0:
                self.message = "❌ Amount must be positive"
                return

            if self.transaction_id:
                # Update existing transaction
                await update_transaction(
                    transaction_id=self.transaction_id,
                    user_id=user_id,
                    amount=float(amount_decimal),
                    category=self.category_selector.category,
                    transaction_type=self.category_selector.transaction_type,
                    account_id=self.account_selector.account_id
                )
                self.message = f"✅ Transaction updated: {amount_decimal} ({self.category_selector.category})"
            else:
                # Create new transaction
                await create_transaction(
                    user_id=user_id,
                    amount=float(amount_decimal),
                    category=self.category_selector.category,
                    transaction_type=self.category_selector.transaction_type,
                    account_id=self.account_selector.account_id
                )
                self.message = f"✅ Transaction created: {amount_decimal} ({self.category_selector.category})"

            # Notify parent component about completion
            await self.call_on_change(update, context)
        except ValueError as e:
            self.message = f"❌ Invalid amount: {inp.value}"
        except Exception as e:
            self.message = f"❌ Error creating transaction: {str(e)}"

    def render(self, update, context):
        """Render the transaction edit UI"""
        return self.account_selector.render(update, context) + self.category_selector.render(update, context)

    def get_message(self):
        """Get current message to display"""
        return self.message

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message):
        """Handle text input messages"""
        if self.amount_input.is_active():
            return await self.amount_input.handle_message(update, context, message)
        return False

    async def handle_callback(self, update, context, callback_data: str) -> bool:
        """Handle button callbacks"""
        handle_account = await self.account_selector.handle_callback(update, context, callback_data)
        handle_category = await self.category_selector.handle_callback(update, context, callback_data)
        return handle_account or handle_category