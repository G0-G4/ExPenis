from typing import List
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

class Component:
    def __init__(self, component_id: str = None):
        self.component_id = component_id or str(id(self))
        
    def render(self) -> InlineKeyboardButton:
        raise NotImplementedError
        
    def handle_callback(self, callback_data: str) -> bool:
        """Return True if callback was handled, False otherwise"""
        return False

class CheckBox(Component):
    def __init__(self, text: str = "", selected: bool = False, group: str = None, 
                 callback_prefix: str = "cb_", on_change: callable = None):
        super().__init__()
        self._selected = selected
        self.text = text
        self.group = group
        self.callback_prefix = callback_prefix
        self.on_change = on_change
        
    def check(self):
        self._selected = True
        
    def uncheck(self):
        self._selected = False
        
    def toggle(self):
        self._selected = not self._selected
        
    @property
    def selected(self):
        return self._selected
        
    @property
    def display_text(self):
        return f"{'✓ ' if self._selected else ''}{self.text}"
        
    def render(self) -> InlineKeyboardButton:
        return InlineKeyboardButton(
            self.display_text,
            callback_data=f"{self.callback_prefix}{self.component_id}"
        )
        
    def handle_callback(self, callback_data: str) -> bool:
        if callback_data.startswith(self.callback_prefix):
            self.toggle()
            if self.on_change:
                self.on_change(self)
            return True
        return False

class CheckBoxGroup:
    def __init__(self, name: str, on_change: callable = None):
        self.name = name
        self.checkboxes = []
        self.on_change = on_change
        
    def add(self, checkbox: CheckBox):
        checkbox.group = self.name
        self.checkboxes.append(checkbox)
        
    def select(self, selected_checkbox: CheckBox):
        for checkbox in self.checkboxes:
            if checkbox is selected_checkbox:
                checkbox.check()
            else:
                checkbox.uncheck()
        if self.on_change:
            self.on_change(selected_checkbox)

class Panel:
    def __init__(self, components: List[Component] = None):
        self.components = components or []
        self._component_map = {c.component_id: c for c in self.components if hasattr(c, 'component_id')}
        
    def add(self, component: Component):
        self.components.append(component)
        if hasattr(component, 'component_id'):
            self._component_map[component.component_id] = component
        
    def render(self) -> InlineKeyboardMarkup:
        keyboard = []
        for component in self.components:
            if isinstance(component, Panel):
                keyboard.extend(component.render().inline_keyboard)
            else:
                keyboard.append([component.render()])
        return InlineKeyboardMarkup(keyboard)
        
    def handle_callback(self, callback_data: str) -> bool:
        # Try to find component by ID
        component_id = callback_data.split('_')[-1] if '_' in callback_data else None
        if component_id and component_id in self._component_map:
            return self._component_map[component_id].handle_callback(callback_data)
            
        # Fallback to checking all components
        for component in self.components:
            if component.handle_callback(callback_data):
                return True
        return False
