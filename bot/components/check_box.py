from bot.components.component import Component
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand

class CheckBox(Component):
    def __init__(self, text: str = "", selected: bool = False,
                 callback_prefix: str = "cb_", on_change: callable = None, component_id = None, group: "CheckBoxGroup" = None):
        super().__init__(component_id, on_change)
        self._selected = selected
        self.text = text
        self.callback_prefix = callback_prefix
        if group:
            self.group = group
            group.add(self)

    async def check(self, notification=False):
        self._selected = True
        if self.on_change:
            await self.call_on_change()
        if not notification and self.group:
            await self.group.notify(self)

    async def uncheck(self, notification=False):
        self._selected = False
        if self.on_change:
            await self.call_on_change()
        if not notification and self.group:
            await self.group.notify(self)

    async def toggle(self, notification=False):
        self._selected = not self._selected
        if self.on_change:
            await self.call_on_change()
        if not notification and self.group:
            await self.group.notify(self)

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

    async def handle_callback(self, callback_data: str) -> bool:
        if callback_data.startswith(f"{self.callback_prefix}{self.component_id}"):
            await self.toggle()
            return True
        return False

class CheckBoxGroup(Component):
    def __init__(self, name: str, on_change: callable = None):
        super().__init__(on_change=on_change)
        self.name = name
        self.checkboxes = []
        self._selected_check_box = None

    def add(self, checkbox: CheckBox):
        self.checkboxes.append(checkbox)

    async def notify(self, selected_checkbox: CheckBox):
        self._selected_check_box = selected_checkbox
        for checkbox in self.checkboxes:
            if checkbox is not selected_checkbox:
                await checkbox.uncheck(notification=True)
        if self.on_change:
            await self.call_on_change()

    @property
    def selected_check_box(self):
        return self._selected_check_box