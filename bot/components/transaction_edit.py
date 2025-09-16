from telegram import Update
from telegram.ext import ContextTypes
from decimal import Decimal

from bot.components.component import MessageHandlerComponent
from bot.components.account_selector import AccountSelector
from bot.components.category_selector import CategorySelector
from bot.components.input import Input
from bot.messages import *
from core.service.transaction_service import create_transaction, get_transaction_by_id, update_transaction


class TransactionEdit(MessageHandlerComponent):
    def __init__(self, accounts=None, balance_map=None, income_categories=None, expense_categories=None, transaction_data=None, component_id: str = None, on_change: callable = None):
        super().__init__(component_id, on_change)
        
        # Initialize with provided data or defaults
        selected_account_id = transaction_data.get('account_id') if transaction_data else None
        selected_category = transaction_data.get('category') if transaction_data else None
        transaction_type = transaction_data.get('type', 'expense') if transaction_data else 'expense'
        
        self.account_selector = AccountSelector(
            accounts=accounts,
            balance_map=balance_map,
            selected_account_id=selected_account_id,
            on_change=self.on_selection_change
        )
        self.category_selector = CategorySelector(
            income_categories=income_categories,
            expense_categories=expense_categories,
            selected_category=selected_category,
            transaction_type=transaction_type,
            on_change=self.on_selection_change
        )
        self.amount_input = Input(on_change=self.on_amount_input)
        
        self.transaction_id = transaction_data.get('id') if transaction_data else None
        self.ready_for_input = bool(selected_account_id and selected_category)
        
        if self.ready_for_input:
            if self.transaction_id:
                self.message = f"Editing transaction: {transaction_data.get('amount', 0)} - Enter new amount or keep current"
            else:
                self.message = TRANSACTION_INPUT_PROMPT
            self.amount_input.activate()
        else:
            self.message = "Please select both account and category first"
        
        self.initiated = True

    def update_data(self, accounts=None, balance_map=None, income_categories=None, expense_categories=None, transaction_data=None):
        """Update component with new data"""
        if accounts is not None or balance_map is not None:
            selected_account_id = transaction_data.get('account_id') if transaction_data else self.account_selector.account_id
            self.account_selector.update_data(
                accounts=accounts,
                balance_map=balance_map,
                selected_account_id=selected_account_id
            )
            
        if income_categories is not None or expense_categories is not None or transaction_data is not None:
            selected_category = transaction_data.get('category') if transaction_data else self.category_selector.category
            transaction_type = transaction_data.get('type', 'expense') if transaction_data else self.category_selector.transaction_type
            self.category_selector.update_data(
                income_categories=income_categories,
                expense_categories=expense_categories,
                selected_category=selected_category,
                transaction_type=transaction_type
            )
        
        if transaction_data:
            self.transaction_id = transaction_data.get('id')
            self.ready_for_input = bool(self.account_selector.account_id and self.category_selector.category)
            
            if self.ready_for_input:
                if self.transaction_id:
                    self.message = f"Editing transaction: {transaction_data.get('amount', 0)} - Enter new amount or keep current"
                else:
                    self.message = TRANSACTION_INPUT_PROMPT
                self.amount_input.activate()
            else:
                self.message = "Please select both account and category first"
        else:
            # For new transactions, always start with fresh state
            self.transaction_id = None
            self.ready_for_input = bool(self.account_selector.account_id and self.category_selector.category)
            if self.ready_for_input:
                self.message = TRANSACTION_INPUT_PROMPT
                self.amount_input.activate()
            else:
                self.message = "Please select both account and category first"
        
        self.initiated = True

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