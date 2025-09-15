from telegram import Update
from telegram.ext import ContextTypes
from typing import Optional, Callable, Any
import logging

from bot.components.component import Component, UiComponent

logger = logging.getLogger(__name__)

class Input(Component):
    def __init__(self, component_id:str = None, on_change: Optional[Callable] = None):
        """
        Initialize the Input component.
        
        Args:
            on_change: Callback function that will be called with the input value
        """
        super().__init__(component_id=component_id, on_change=on_change)
        self.value = None
        self._is_active = False

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message) -> bool:
        """
        Handle incoming text messages.
        
        Args:
            update: Telegram update object
            context: Telegram context object
            message: Telegram message object
            
        Returns:
            bool: True if message was handled, False otherwise
        """
        if not message or not message.text:
            return False
            
        if not self._is_active:
            return False
            
        self.value = message.text.strip()
        
        await self.call_on_change(update, context)

        self._is_active = False
        return True

    def activate(self):
        """Activate the input to start accepting messages"""
        self._is_active = True
        self.value = None

    def deactivate(self):
        """Deactivate the input to stop accepting messages"""
        self._is_active = False

    def get_value(self) -> Optional[str]:
        """Get the current input value"""
        return self.value

    def is_active(self) -> bool:
        """Check if input is currently active and accepting messages"""
        return self._is_active
