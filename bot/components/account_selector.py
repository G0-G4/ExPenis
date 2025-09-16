import asyncio

from telegram import Update
from telegram.ext import Application
from telegram.error import BadRequest
from typing import Optional

from bot.components.check_box import CheckBox, CheckBoxGroup
from bot.components.component import UiComponent
from bot.components.panel import Panel
from bot.messages import *
from bot.bot_config import *
from core.service.account_service import get_user_accounts, calculate_account_balance
from core.service.category_service import ensure_user_has_categories
from core.helpers import format_amount
class AccountSelector(UiComponent):

    def __init__(self, on_change: callable = None):
        super().__init__(on_change=on_change)
        self.accounts = None
        self.clear()
    def clear(self):
        self.account_id = None
        self.accounts = []
        self.balance_map = {}
        self.panel  = Panel()
        self.initiated = False
        self.selected_account = None

    async def init(self, user_id):
        # Clear panel to avoid duplicates
        self.panel = Panel()
        
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
    async def account_selection_call_back(self, cbg: CheckBoxGroup, update, context):
        if cbg.selected_check_box is not None:
            if cbg.selected_check_box.selected:
                self.account_id = int(cbg.selected_check_box.component_id.split("_")[1])
                # todo refactor to avoid loop
                for account in self.accounts:
                    if account.id == self.account_id:
                        self.selected_account = account
            else:
                self.account_id = None
        await self.call_on_change(update, context)

    async def handle_callback(self, update, context, callback_data: str) -> bool:
        return await self.panel.handle_callback(update, context, callback_data)

    def render(self, update, context):
        return self.panel.render(update, context)