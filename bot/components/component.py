import asyncio
from abc import ABC, abstractmethod


class Component(ABC):
    """Base component class providing core functionality"""

    def __init__(self, component_id: str = None, on_change: callable = None):
        self.component_id = component_id or str(id(self))
        self.on_change = on_change

    async def call_on_change(self, update, context):
        if not self.on_change:
            return
        if asyncio.iscoroutinefunction(self.on_change):
            await self.on_change(self, update, context)
        else:
            self.on_change(self, update, context)


class StatefulComponent(Component):
    """Component with lifecycle management and state"""

    def __init__(self, component_id: str = None, on_change: callable = None):
        super().__init__(component_id, on_change)
        self.initiated = False

    def update_data(self, **kwargs):
        """Update component data - override in subclasses"""
        self.initiated = True


class UiComponent(StatefulComponent):
    """Component that renders UI elements"""

    def __init__(self, component_id: str = None, on_change: callable = None):
        super().__init__(component_id, on_change)

    @abstractmethod
    def render(self, update, context):
        """Render component UI elements"""
        raise NotImplementedError

    @abstractmethod
    async def handle_callback(self, update, context, callback_data: str) -> bool:
        """Handle callback queries. Return True if callback was handled, False otherwise"""
        raise NotImplementedError

    @abstractmethod
    def get_message(self):
        """Get message text for this component"""
        raise NotImplementedError


class MessageHandlerComponent(UiComponent):
    """Component that can handle text message input from users"""

    def __init__(self, component_id: str = None, on_change: callable = None):
        super().__init__(component_id, on_change)

    @abstractmethod
    async def handle_message(self, update, context, message):
        """Handle text messages. Return True if message was handled, False otherwise"""
        raise NotImplementedError
