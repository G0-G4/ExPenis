from typing import List

from bot.components.component import Component


class Panel(Component):
    def __init__(self, components: List[Component] = None, per_row:int = 3):
        super().__init__()
        self.components = components or []
        self._component_map = {c.component_id: c for c in self.components}
        self._per_row = per_row

    def add(self, component: Component):
        self.components.append(component)
        self._component_map[component.component_id] = component

    def render(self) -> list:
        keyboard = []
        row = []
        for component in self.components:
            if len(row) == self._per_row:
                keyboard.append(row)
                row = []
            else:
                if isinstance(component, Panel):
                    keyboard.extend(component.render())
                else:
                    row.append(component.render())
        if len(row):
            keyboard.append(row)
        return keyboard

    async def handle_callback(self, callback_data: str) -> bool:
        # Try to find component by ID
        component_id = callback_data.split('_')[-1] if '_' in callback_data else None
        if component_id and component_id in self._component_map:
            return await self._component_map[component_id].handle_callback(callback_data)

        # Fallback to checking all components
        for component in self.components:
            if await component.handle_callback(callback_data):
                return True
        return False