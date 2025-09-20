from typing import List

from bot.components.component import UiComponent


class Panel(UiComponent):
    def __init__(self, components: List[UiComponent] = None, per_row:int = 3):
        super().__init__()
        self.components = components or []
        self._component_map = {c.component_id: c for c in self.components}
        self._per_row = per_row
        self.initiated = True

    def add(self, component: UiComponent):
        self.components.append(component)
        self._component_map[component.component_id] = component

    def render(self, update, context) -> list:
        keyboard = []
        row = []
        for component in self.components:
            if isinstance(component, Panel):
                keyboard.extend(component.render(update, context))
            else:
                row.append(component.render(update, context))
            if len(row) == self._per_row:
                keyboard.append(row)
                row = []
        if len(row):
            keyboard.append(row)
        return keyboard

    async def handle_callback(self, update, context, callback_data: str) -> bool:
        # Try to find component by ID
        component_id = callback_data.split('_')[-1] if '_' in callback_data else None
        if component_id and component_id in self._component_map:
            return await self._component_map[component_id].handle_callback(update, context, callback_data)

        # Fallback to checking all components
        for component in self.components:
            if await component.handle_callback(update, context, callback_data):
                return True
        return False

    def update_data(self, components=None, per_row=None):
        """Update panel data"""
        if components is not None:
            self.components = components
            self._component_map = {c.component_id: c for c in self.components}
        if per_row is not None:
            self._per_row = per_row
        self.initiated = True

    def get_message(self):
        """Get message for panel - panels typically don't have their own message"""
        return ""