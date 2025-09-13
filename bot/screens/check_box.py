import asyncio
from typing import List
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import inspect
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, ContextTypes, CallbackQueryHandler
from telegram.error import BadRequest
from typing import Optional

from bot.messages import *
from bot.bot_config import *
from core.service.account_service import get_user_accounts, calculate_account_balance
from core.service.category_service import ensure_user_has_categories
from core.helpers import format_amount

class Component:
    def __init__(self, component_id: str = None):
        self.component_id = component_id or str(id(self))
        
    def render(self) -> InlineKeyboardButton:
        raise NotImplementedError
        
    async def handle_callback(self, callback_data: str) -> bool:
        """Return True if callback was handled, False otherwise"""
        return False

    # async def call_on_change(self):
    #     if not self.()
    #     if inspect.iscoroutinefunction(self.on_change):
    #         await self.on_change(self)
    #     else:
    #         self.on_change(self)

class CheckBox(Component):
    def __init__(self, text: str = "", selected: bool = False,
                 callback_prefix: str = "cb_", on_change: callable = None, component_id = None, group: "CheckBoxGroup" = None):
        super().__init__(component_id)
        self._selected = selected
        self.text = text
        self.callback_prefix = callback_prefix
        self.on_change = on_change
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

    async def call_on_change(self):
        if inspect.iscoroutinefunction(self.on_change):
            await self.on_change(self)
        else:
            self.on_change(self)

    @property
    def selected(self):
        return self._selected
        
    @property
    def display_text(self):
        return f"{'✓ ' if self._selected else ''}{self.text}"

    # @property
    # def component_id(self):
    #     return self.component_id

        
    def render(self) -> InlineKeyboardButton:
        return InlineKeyboardButton(
            self.display_text,
            callback_data=f"{self.callback_prefix}{self.component_id}"
        )
        
    async def handle_callback(self, callback_data: str) -> bool:
        if callback_data.startswith(f"{self.callback_prefix}{self.component_id}"):
            await self.toggle()
            # if self.on_change:
            #     self.on_change(self)
            return True
        return False

class CheckBoxGroup:
    def __init__(self, name: str, on_change: callable = None):
        self.name = name
        self.checkboxes = []
        self.on_change = on_change
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

    async def call_on_change(self):
        if inspect.iscoroutinefunction(self.on_change):
            await self.on_change(self)
        else:
            self.on_change(self)

    @property
    def selected_check_box(self):
        return self._selected_check_box


class Panel(Component):
    def __init__(self, components: List[Component] = None, per_row:int = 3):
        super().__init__()
        self.components = components or []
        self._component_map = {c.component_id: c for c in self.components}
        self._per_row = per_row
        
    def add(self, component: Component):
        self.components.append(component)
        if hasattr(component, 'component_id'):
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

class Screen:

    def __init__(self, message: str = ""):
        self.panel = Panel()
        self.initiated = False
        self.message = message

    # async def _init(self, user_id, *args, **kwargs):
    #     raise NotImplementedError

    async def handle_user_presses(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        raise NotImplementedError

    async def display_on(self, update: Update, text: str, markup):
        """Display the panel on the given update"""
        try:
            if update.message:
                await update.message.reply_text(
                    text=text,
                    reply_markup=InlineKeyboardMarkup(markup.render()),
                    parse_mode="HTML"
                )
            elif update.callback_query:
                await update.callback_query.edit_message_text(
                    text=text,
                    reply_markup=InlineKeyboardMarkup(markup.render()),
                    parse_mode="HTML"
                )
        except BadRequest as e:
            print(f"No modifications needed: {e.message}")
