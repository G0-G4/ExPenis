import asyncio

from telegram import Update
from telegram.ext import Application
from telegram.error import BadRequest
from typing import Optional

from bot.components.check_box import CheckBox, CheckBoxGroup
from bot.components.component import Component
from bot.components.panel import Panel
from bot.messages import *
from bot.bot_config import *
from bot.screens.check_box import Screen
from core.service.account_service import get_user_accounts, calculate_account_balance
from core.service.category_service import ensure_user_has_categories
from core.helpers import format_amount
class CategorySelector(Component):

    def __init__(self, transaction_type='expense', on_change:callable=None):
        super().__init__(on_change=on_change)
        self.income_cats = []
        self.expense_cats = []
        self.transaction_type = transaction_type
        self.category = None
        self.panel = None
        self.category_map = {}
        self.initiated = False
        self.on_change = on_change

    async def init(self, user_id: int, update: Update, transaction_type='expense'):
        self.panel = Panel()
        self.transaction_type = transaction_type
        async def decorated(x):
            await self._handle_type_change(x, update)
        self.income_cats, self.expense_cats = await ensure_user_has_categories(user_id)
        type_group = CheckBoxGroup("type_group",
                                   on_change=decorated)
        income_cb = CheckBox(
            "🟢 Income (+)",
            self.transaction_type == 'income',
            component_id="income",
            group=type_group
        )
        expense_cb = CheckBox(
            "🔴 Expense (-)",
            self.transaction_type == 'expense',
            component_id="expense",
            group=type_group
        )
        type_panel = Panel()
        type_panel.add(income_cb)
        type_panel.add(expense_cb)

        category_panel = Panel()
        category_group = CheckBoxGroup("categories",
                                       on_change=self._handle_category_change)
        cats = self.expense_cats if self.transaction_type == 'expense' else self.income_cats
        for category in cats:
            cb = CheckBox(
                category.name,
                category.name == self.category,
                component_id=f"cat_{category.id}",
                group=category_group
            )
            category_group.add(cb)
            category_panel.add(cb)
        for category in self.expense_cats + self.income_cats:
            self.category_map[category.id] = category

        self.panel.add(type_panel)
        self.panel.add(category_panel)
        self.initiated = True

    async def call_on_change(self):
        if not self.on_change:
            return
        if asyncio.iscoroutinefunction(self.on_change):
            await self.on_change(self)
        else:
            self.on_change(self)

    async def handle_callback(self, callback_data: str) -> bool:
        return await self.panel.handle_callback(callback_data)

    async def _handle_type_change(self, cbg: CheckBoxGroup, update: Update):
        if cbg.selected_check_box is not None:
            if cbg.selected_check_box.selected:
                self.transaction_type = cbg.selected_check_box.component_id
                user_id  = update.callback_query.from_user.id
                await self.init(user_id, update, self.transaction_type)
            else:
                self.transaction_type= None
        print("type set to " + str(self.transaction_type))
        await self.call_on_change()

    async def _handle_category_change(self, cbg: CheckBoxGroup):
        if cbg.selected_check_box is not None:
            if cbg.selected_check_box.selected:
                category_id = int(cbg.selected_check_box.component_id.split("_")[1])
                self.category = self.category_map[category_id].name
            else:
                self.category = None
        print("category set " + self.category)
        await self.call_on_change()

    def render(self):
        return self.panel.render()
