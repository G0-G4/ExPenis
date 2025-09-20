from telegram import Update
from telegram.ext import ContextTypes
from decimal import Decimal
from typing import Optional, Callable

from bot.components.component import MessageHandlerComponent
from bot.components.account_selector import AccountSelector
from bot.components.delete_dialog import DeleteDialog
from bot.components.button import Button
from bot.components.input import Input
from bot.messages import ADD_ACCOUNT_MESSAGE, ADD_ACCOUNT_AMOUNT_MESSAGE, ACCOUNT_CREATED_MESSAGE
from core.service.account_service import create_account, delete_account
from core.models.account import Account


class AccountEdit(MessageHandlerComponent):
    def __init__(self, 
                 accounts=None, 
                 balance_map=None, 
                 component_id: str = None, 
                 on_change: Optional[Callable] = None):
        super().__init__(component_id, on_change)
        
        self.accounts = accounts or []
        self.balance_map = balance_map or {}
        self.selected_account_id = None
        self.state = "select"  # select | name_input | amount_input
        
        # Components
        self.account_selector = AccountSelector(
            accounts=accounts,
            balance_map=balance_map,
            on_change=self._on_account_selected
        )
        
        self.delete_dialog = DeleteDialog(
            message="Are you sure you want to delete this account and all its transactions?",
            trigger_text="🗑 Delete Account",
            on_confirm=self._on_delete_confirm,
        )
        
        self.create_button = Button(
            text="➕ Create Account",
            callback_data=f"create_account_{id(self)}",
            on_click=self._on_create_click
        )
        
        self.name_input = Input(on_change=self._on_name_input)
        self.amount_input = Input(on_change=self._on_amount_input)
        
        self._update_message()
        self.initiated = True

    def _update_message(self):
        """Update the message based on current state"""
        if self.state == "name_input":
            self.message = ADD_ACCOUNT_MESSAGE
        elif self.state == "amount_input":
            self.message = ADD_ACCOUNT_AMOUNT_MESSAGE
        elif self.selected_account_id:
            account = self._get_selected_account()
            self.message = f"Selected account: {account.name}" if account else "Select an account"
        else:
            self.message = "Select an account or create new one"

    def _get_selected_account(self) -> Optional[Account]:
        """Get currently selected account object"""
        if not self.selected_account_id:
            return None
        return next((acc for acc in self.accounts if acc.id == self.selected_account_id), None)

    def update_data(self, accounts=None, balance_map=None):
        """Update component with new data"""
        if accounts is not None:
            self.accounts = accounts
        if balance_map is not None:
            self.balance_map = balance_map
            
        self.account_selector.update_data(
            accounts=accounts,
            balance_map=balance_map,
            selected_account_id=self.selected_account_id
        )
        self._update_message()
        self.initiated = True

    async def _on_account_selected(self, component, update, context):
        """Handle account selection"""
        self.selected_account_id = component.account_id
        self.state = "select"
        self._update_message()
        await self.call_on_change(update, context)

    async def _on_create_click(self, button, update, context):
        """Handle create account button click"""
        self.state = "name_input"
        self.name_input.activate()
        self._update_message()
        await self.call_on_change(update, context)

    async def _on_name_input(self, inp: Input, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle account name input"""
        self.new_account_name = inp.value.strip()
        if not self.new_account_name:
            self.message = "⚠️ Account name cannot be empty"
            return
            
        self.state = "amount_input"
        self.amount_input.activate()
        self._update_message()
        await self.call_on_change(update, context)

    async def _on_amount_input(self, inp: Input, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle account amount input"""
        try:
            amount = Decimal(inp.value)
            user_id = update.message.from_user.id
            
            # Create the new account
            account = await create_account(
                user_id=user_id,
                name=self.new_account_name,
                initial_amount=float(amount)
            )
            
            self.message = f"{ACCOUNT_CREATED_MESSAGE}\nName: {account.name}\nAmount: {amount}"
            self.state = "select"
            self.new_account_name = None
            
            # Refresh accounts list
            await self.call_on_change(update, context)
            
        except (ValueError, TypeError):
            self.message = "⚠️ Please enter a valid number for the amount"

    async def _on_delete_confirm(self, dialog, update, context):
        """Handle account deletion confirmation"""
        if self.selected_account_id:
            user_id = update.callback_query.from_user.id
            success = await delete_account(self.selected_account_id, user_id)
            if success:
                self.message = "✅ Account deleted successfully"
                self.selected_account_id = None
            else:
                self.message = "❌ Failed to delete account"
            
            await self.call_on_change(update, context)

    def render(self, update, context):
        """Render the account edit UI"""
        keyboard = self.account_selector.render(update, context)
        
        # Add action buttons
        action_row = [self.create_button.render(update, context)]

        keyboard.append(action_row)
        if self.selected_account_id or self.delete_dialog.visible:
            keyboard.extend(self.delete_dialog.render(update, context))  # Get trigger button

        return keyboard

    def get_message(self):
        """Get current message to display"""
        if self.delete_dialog.visible:
            return self.delete_dialog.get_message()
        return self.message

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message):
        """Handle text input messages"""
        if self.state == "name_input" and self.name_input.is_active():
            return await self.name_input.handle_message(update, context, message)
        elif self.state == "amount_input" and self.amount_input.is_active():
            return await self.amount_input.handle_message(update, context, message)
        return False

    async def handle_callback(self, update, context, callback_data: str) -> bool:
        """Handle button callbacks"""
        # Handle delete dialog
        if await self.delete_dialog.handle_callback(update, context, callback_data):
            return True
            
        # Handle create button
        if callback_data == f"create_account_{id(self)}":
            return await self.create_button.handle_callback(update, context, callback_data)
            
        # Handle account selection
        return await self.account_selector.handle_callback(update, context, callback_data)
