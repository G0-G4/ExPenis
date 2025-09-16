from bot.components.component import UiComponent
from bot.components.button import Button


class DeleteDialog(UiComponent):
    def __init__(self, message: str = "Are you sure you want to delete?", 
                 trigger_text: str = "🗑 Delete", trigger_callback_data: str = None,
                 on_confirm: callable = None, on_cancel: callable = None, component_id: str = None):
        super().__init__(component_id, on_confirm)
        self.message = message
        self.trigger_text = trigger_text
        self.trigger_callback_data = trigger_callback_data or f"delete_trigger_{component_id}"
        self.on_confirm = on_confirm
        self.on_cancel = on_cancel
        self.visible = False
        
        self._build_ui()
        self.initiated = True
        
    def _build_ui(self):
        """Build UI components from current data"""
        self.trigger_button = Button(
            text=self.trigger_text,
            callback_data=self.trigger_callback_data,
            on_click=self._on_trigger_click
        )
        
        self.cancel_button = Button(
            text="❌ Cancel", 
            callback_data=f"delete_cancel_{self.component_id}",
            on_click=self._on_cancel_click
        )
        
        self.delete_button = Button(
            text="🗑 Delete", 
            callback_data=f"delete_confirm_{self.component_id}",
            on_click=self._on_confirm_click
        )
        
    def update_data(self, message=None, trigger_text=None, trigger_callback_data=None, on_confirm=None, on_cancel=None):
        """Update component data and rebuild UI"""
        if message is not None:
            self.message = message
        if trigger_text is not None:
            self.trigger_text = trigger_text
        if trigger_callback_data is not None:
            self.trigger_callback_data = trigger_callback_data
        if on_confirm is not None:
            self.on_confirm = on_confirm
        if on_cancel is not None:
            self.on_cancel = on_cancel
            
        self._build_ui()
        self.initiated = True
    
    async def show(self, update, context):
        self.visible = True
        
    async def hide(self, update, context):
        self.visible = False
    
    async def _on_trigger_click(self, button, update, context):
        await self.show(update, context)
        
    async def _on_cancel_click(self, button, update, context):
        await self.hide(update, context)
        if self.on_cancel:
            await self.on_cancel(self, update, context)
    
    async def _on_confirm_click(self, button, update, context):
        await self.hide(update, context)
        if self.on_confirm:
            await self.on_confirm(self, update, context)
    
    def render(self, update, context):
        if self.visible:
            # Show confirmation dialog
            return [
                [self.cancel_button.render(update, context), self.delete_button.render(update, context)]
            ]
        else:
            # Show trigger button
            return [
                [self.trigger_button.render(update, context)]
            ]
    
    async def handle_callback(self, update, context, callback_data: str) -> bool:
        # Handle trigger button when dialog is not visible
        if not self.visible:
            return await self.trigger_button.handle_callback(update, context, callback_data)
        
        # Handle dialog buttons when visible    
        handled = await self.cancel_button.handle_callback(update, context, callback_data)
        if not handled:
            handled = await self.delete_button.handle_callback(update, context, callback_data)
        
        return handled

    def get_message(self):
        """Get delete dialog message"""
        if self.visible:
            return self.message
        return ""