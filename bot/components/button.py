from bot.components.component import UiComponent
from telegram import InlineKeyboardButton


class Button(UiComponent):
    def __init__(self, text: str, callback_data: str = None, on_click: callable = None, component_id: str = None):
        super().__init__(component_id, on_click)
        self.text = text
        self.callback_data = callback_data or f"btn_{self.component_id}"
        self.initiated = True
        
    async def click(self, update, context):
        if self.on_change:
            await self.call_on_change(update, context)
    
    def render(self, update, context) -> InlineKeyboardButton:
        return InlineKeyboardButton(
            self.text,
            callback_data=self.callback_data
        )
    
    async def handle_callback(self, update, context, callback_data: str) -> bool:
        if callback_data == self.callback_data:
            await self.click(update, context)
            return True
        return False

    def update_data(self, text=None, callback_data=None):
        """Update button data"""
        if text is not None:
            self.text = text
        if callback_data is not None:
            self.callback_data = callback_data
        self.initiated = True

    def get_message(self):
        """Get button message"""
        return f"Button: {self.text}"