from bot.components.component import UiComponent
from telegram import InlineKeyboardButton


class Button(UiComponent):
    def __init__(self, text: str, callback_data: str = None, on_click: callable = None, component_id: str = None):
        super().__init__(component_id, on_click)
        self.text = text
        self.callback_data = callback_data or f"btn_{self.component_id}"
        
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