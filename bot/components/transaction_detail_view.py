from bot.components.component import UiComponent
from bot.components.button import Button
from bot.components.delete_dialog import DeleteDialog
from core.helpers import format_amount
from core.service.transaction_service import get_transaction_by_id, delete_transaction
from core.models.transaction import Transaction
from telegram import InlineKeyboardMarkup


class TransactionDetailView(UiComponent):
    def __init__(self, transaction_id: int, user_id: int, on_edit: callable = None, on_back: callable = None, component_id: str = None):
        super().__init__(component_id, None)
        self.transaction_id = transaction_id
        self.user_id = user_id
        self.transaction = None
        self.on_edit = on_edit
        self.on_back = on_back
        self.view_mode = "detail"  # "detail", "delete_confirm"
        
        # Create buttons
        self.edit_button = Button(
            text="✏️ Edit",
            callback_data=f"edit_transaction_{self.component_id}",
            on_click=self._on_edit_click
        )
        
        self.delete_button = Button(
            text="🗑 Delete",
            callback_data=f"show_delete_dialog_{self.component_id}",
            on_click=self._on_delete_click
        )
        
        self.back_button = Button(
            text="← Back",
            callback_data=f"back_from_transaction_{self.component_id}",
            on_click=self._on_back_click
        )
        
        # Create delete dialog
        self.delete_dialog = DeleteDialog(
            message="Are you sure you want to delete this transaction?",
            on_confirm=self._on_delete_confirm,
            on_cancel=self._on_delete_cancel,
            component_id=f"delete_{self.component_id}"
        )
    
    async def init(self):
        """Initialize by loading transaction data"""
        self.transaction = await get_transaction_by_id(self.transaction_id)
    
    async def _on_edit_click(self, button, update, context):
        if self.on_edit:
            await self.on_edit(self, update, context)
    
    async def _on_delete_click(self, button, update, context):
        self.view_mode = "delete_confirm"
        await self.delete_dialog.show(update, context)
    
    async def _on_back_click(self, button, update, context):
        if self.on_back:
            await self.on_back(self, update, context)
    
    async def _on_delete_confirm(self, dialog, update, context):
        # Delete the transaction
        success = await delete_transaction(self.transaction_id, self.user_id)
        if success:
            self.view_mode = "detail"
            if self.on_back:
                await self.on_back(self, update, context)
    
    async def _on_delete_cancel(self, dialog, update, context):
        self.view_mode = "detail"
    
    def get_message(self):
        """Get the transaction detail message"""
        if not self.transaction:
            return "Transaction not found"
        
        emoji = "🟢" if self.transaction.type == "income" else "🔴"
        type_text = "Income" if self.transaction.type == "income" else "Expense"
        formatted_amount = format_amount(self.transaction.amount)
        
        message = f"{emoji} <b>{type_text}</b>\n\n"
        message += f"💰 Amount: <b>{formatted_amount}</b>\n"
        message += f"📂 Category: <b>{self.transaction.category}</b>\n"
        message += f"📅 Date: <b>{self.transaction.created_at.strftime('%Y-%m-%d %H:%M')}</b>\n"
        
        if self.view_mode == "delete_confirm":
            message += f"\n{self.delete_dialog.message}"
        
        return message
    
    def render(self, update, context):
        """Render the transaction detail view"""
        if self.view_mode == "delete_confirm":
            return self.delete_dialog.render(update, context)
        
        # Normal detail view
        return [
            [self.edit_button.render(update, context), self.delete_button.render(update, context)],
            [self.back_button.render(update, context)]
        ]
    
    async def handle_callback(self, update, context, callback_data: str) -> bool:
        # Handle delete dialog callbacks first
        if await self.delete_dialog.handle_callback(update, context, callback_data):
            return True
        
        # Handle button callbacks
        handled = await self.edit_button.handle_callback(update, context, callback_data)
        if not handled:
            handled = await self.delete_button.handle_callback(update, context, callback_data)
        if not handled:
            handled = await self.back_button.handle_callback(update, context, callback_data)
        
        return handled