import asyncio

class Component:
    def __init__(self, component_id: str = None, on_change: callable = None):
        self.component_id = component_id or str(id(self))
        self.on_change = on_change
    def render(self):
        raise NotImplementedError

    async def handle_callback(self, callback_data: str) -> bool:
        """Return True if callback was handled, False otherwise"""
        return False

    async def call_on_change(self):
        if not self.on_change:
            return
        if asyncio.iscoroutinefunction(self.on_change):
            await self.on_change(self)
        else:
            self.on_change(self)