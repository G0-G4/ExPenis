from bot.components.component import UiComponent
from bot.components.button import Button


class DeleteDialog(UiComponent):
    def __init__(self, message: str = "Are you sure you want to delete?", 
                 on_confirm: callable = None, on_cancel: callable = None, component_id: str = None):
        super().__init__(component_id, on_confirm)
        self.message = message
        self.on_confirm = on_confirm
        self.on_cancel = on_cancel
        self.visible = False
        
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
    
    async def show(self, update, context):
        self.visible = True
        
    async def hide(self, update, context):
        self.visible = False
        
    async def _on_cancel_click(self, button, update, context):
        await self.hide(update, context)
        if self.on_cancel:
            await self.on_cancel(self, update, context)
    
    async def _on_confirm_click(self, button, update, context):
        await self.hide(update, context)
        if self.on_confirm:
            await self.on_confirm(self, update, context)
    
    def render(self, update, context):
        if not self.visible:
            return []
        
        return [
            [self.cancel_button.render(update, context), self.delete_button.render(update, context)]
        ]
    
    async def handle_callback(self, update, context, callback_data: str) -> bool:
        if not self.visible:
            return False
            
        handled = await self.cancel_button.handle_callback(update, context, callback_data)
        if not handled:
            handled = await self.delete_button.handle_callback(update, context, callback_data)
        
        return handled

    async def init(self, update, context, *args, **kwargs):
        """Initialize delete dialog and buttons"""
        await self.cancel_button.init(update, context, *args, **kwargs)
        await self.delete_button.init(update, context, *args, **kwargs)
        self.initiated = True

    async def clear_state(self, update, context):
        """Clear delete dialog state"""
        await self.cancel_button.clear_state(update, context)
        await self.delete_button.clear_state(update, context)
        self.visible = False
        self.initiated = False

    async def get_message(self, update, context):
        """Get delete dialog message"""
        if self.visible:
            return self.message
        return ""