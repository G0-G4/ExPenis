from bot.components.component import UiComponent
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand

class CheckBox(UiComponent):
    def __init__(self, text: str = "", selected: bool = False,
                 callback_prefix: str = "cb_", on_change: callable = None, component_id = None, group: "CheckBoxGroup" = None):
        super().__init__(component_id, on_change)
        self._selected = selected
        self.text = text
        self.callback_prefix = callback_prefix
        if group:
            self.group = group
            group.add(self)

    async def check(self, update, context, notification=False):
        self._selected = True
        if self.on_change:
            await self.call_on_change(update, context)
        if not notification and self.group:
            await self.group.notify(update, context, self)

    async def uncheck(self, update, context, notification=False):
        self._selected = False
        if self.on_change:
            await self.call_on_change(update, context)
        if not notification and self.group:
            await self.group.notify(update, context, self)

    async def toggle(self, update, context, notification=False):
        self._selected = not self._selected
        if self.on_change:
            await self.call_on_change(update, context)
        if not notification and self.group:
            await self.group.notify(update, context, self)

    @property
    def selected(self):
        return self._selected

    @property
    def display_text(self):
        return f"{'✓ ' if self._selected else ''}{self.text}"

    def render(self, update, context) -> InlineKeyboardButton:
        return InlineKeyboardButton(
            self.display_text,
            callback_data=f"{self.callback_prefix}{self.component_id}"
        )

    async def handle_callback(self, update, context, callback_data: str) -> bool:
        if callback_data.startswith(f"{self.callback_prefix}{self.component_id}"):
            await self.toggle(update, context)
            return True
        return False

    async def init(self, update, context, *args, **kwargs):
        """Initialize checkbox"""
        self.initiated = True

    async def clear_state(self, update, context):
        """Clear checkbox state"""
        self._selected = False
        self.initiated = False

    async def get_message(self, update, context):
        """Get checkbox message"""
        return f"Checkbox: {self.display_text}"

class CheckBoxGroup(UiComponent):
    def __init__(self, name: str, on_change: callable = None):
        super().__init__(on_change=on_change)
        self.name = name
        self.checkboxes = []
        self._selected_check_box = None

    def add(self, checkbox: CheckBox):
        self.checkboxes.append(checkbox)

    async def notify(self, update, context, selected_checkbox: CheckBox):
        self._selected_check_box = selected_checkbox
        for checkbox in self.checkboxes:
            if checkbox is not selected_checkbox:
                await checkbox.uncheck(update, context, notification=True)
        if self.on_change:
            await self.call_on_change(update, context)

    @property
    def selected_check_box(self):
        return self._selected_check_box

    def render(self, update, context):
        return [cb.render(update, context) for cb in self.checkboxes]

    async def handle_callback(self, update, context, callback_data: str) -> bool:
        for cb in self.checkboxes:
            if await cb.handle_callback(update, context, callback_data):
                return True
        return False

    async def init(self, update, context, *args, **kwargs):
        """Initialize checkbox group and all checkboxes"""
        for cb in self.checkboxes:
            await cb.init(update, context, *args, **kwargs)
        self.initiated = True

    async def clear_state(self, update, context):
        """Clear checkbox group state"""
        for cb in self.checkboxes:
            await cb.clear_state(update, context)
        self._selected_check_box = None
        self.initiated = False

    async def get_message(self, update, context):
        """Get checkbox group message"""
        if self._selected_check_box:
            return f"Selected: {self._selected_check_box.text}"
        return f"Checkbox group: {self.name}"
