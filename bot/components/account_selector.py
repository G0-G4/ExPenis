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
class AccountSelector(Component):

    def __init__(self, on_change: callable = None):
        super().__init__(on_change=on_change)
        self.on_change = on_change
        self.account_id = None
        self.accounts = []
        self.balance_map = {}
        self.panel  = Panel()
        self.initiated = False
        self.selected_account = None

    async def init(self, user_id):
        self.accounts = await get_user_accounts(user_id)
        for account in self.accounts:
            balance = await calculate_account_balance(account.id, user_id)
            self.balance_map[account.id] = balance

        # Account selection
        account_group = CheckBoxGroup("accounts",
                                      on_change=self.account_selection_call_back)
        for account in self.accounts:
            cb = CheckBox(
                f"{account.name} ({format_amount(self.balance_map[account.id])})",
                selected=self.account_id == account.id,
                component_id="acc_" + str(account.id),
                group=account_group
            )
            self.panel.add(cb)
        self.initiated = True
    async def account_selection_call_back(self, cbg: CheckBoxGroup):
        if cbg.selected_check_box is not None:
            if cbg.selected_check_box.selected:
                self.account_id = int(cbg.selected_check_box.component_id.split("_")[1])
                # todo refactor to avoid loop
                for account in self.accounts:
                    if account.id == self.account_id:
                        self.selected_account = account
            else:
                self.account_id = None
        print("account set to " + str(self.account_id))
        if self.on_change:
            await self.call_on_change()

    async def call_on_change(self):
        if asyncio.iscoroutinefunction(self.on_change):
            await self.on_change(self)
        else:
            self.on_change(self)

    async def handle_callback(self, callback_data: str) -> bool:
        return await self.panel.handle_callback(callback_data)

    def render(self):
        return self.panel.render()