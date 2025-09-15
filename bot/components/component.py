import asyncio
from abc import ABC, abstractmethod


class Component(ABC):

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


class UiComponent(Component):
    def __init__(self, component_id: str = None, on_change: callable = None):
        super().__init__(component_id, on_change)

    @abstractmethod
    def render(self, update, context):
        raise NotImplementedError

    @abstractmethod
    async def handle_callback(self, update, context, callback_data: str) -> bool:
        """Return True if callback was handled, False otherwise"""
        return False
