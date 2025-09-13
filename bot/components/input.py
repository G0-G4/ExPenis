from telegram import Update
from telegram.ext import ContextTypes
from typing import Optional, Callable, Any
import logging

logger = logging.getLogger(__name__)

class Input:
    def __init__(self, on_input: Optional[Callable] = None):
        """
        Initialize the Input component.
        
        Args:
            on_input: Callback function that will be called with the input value
        """
        self.value = None
        self.on_input = on_input
        self._is_active = False

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """
        Handle incoming text messages.
        
        Args:
            update: Telegram update object
            context: Telegram context object
            
        Returns:
            bool: True if message was handled, False otherwise
        """
        if not update.message or not update.message.text:
            return False
            
        if not self._is_active:
            return False
            
        self.value = update.message.text.strip()
        
        if self.on_input:
            try:
                await self.on_input(self, update, context)
            except Exception as e:
                logger.error(f"Error in input callback: {e}")
                return False
                
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
