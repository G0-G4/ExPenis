from typing import ClassVar, Sequence

from telegram import InlineKeyboardButton, Update
from telegram.ext import ContextTypes
from tuican import get_user_id
from tuican.components import Button, Component, Input, Screen, ScreenGroup
from tuican.validation import any_float, identity

from .delete_screen import DeleteScreen
from ..components.transaction_screen import render_by_n
from ...core.helpers import format_amount
from ...core.models.account import Account
from ...core.service import delete_account_by_id, get_user_accounts_with_balance
from ...core.service import create_account, get_user_account_with_balance, update_account


class AccountsScreen(Screen):
    def __init__(self, group: ScreenGroup):
        self.group = group
        self.new = Button(text="➕ new", on_change=self.new_handler)
        self.accounts = None
        self.account_buttons = []
        super().__init__([self.new], message="список счетов")

    async def get_layout(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> Sequence[
        Sequence[InlineKeyboardButton]]:
        await self.init_if_necessary(update, context)
        return [
            *render_by_n(update, context, self.account_buttons),
            [self.new.render(update, context)]
        ]

    async def new_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        self.remove_accounts()
        screen = AccountCreateScreen(self.group)
        await self.group.go_to_screen(update, context, screen)

    async def edit_account_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE,
                                   callback_data: str | None, cmp: Component):
        self.remove_accounts()
        screen = AccountEditScreen(int(cmp.component_id), self.group)
        await self.group.go_to_screen(update, context, screen)

    async def init_if_necessary(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if self.accounts is None:
            user_id = get_user_id(update)
            accounts_with_balance = await get_user_accounts_with_balance(user_id)
            if len(accounts_with_balance) > 0:
                self.accounts = []
            for account, balance in accounts_with_balance:
                btn = Button(text=f"{account.name} {format_amount(balance)}", component_id=str(account.id),
                             on_change=self.edit_account_handler)
                self.account_buttons.append(btn)
                self.add_component(btn)
                self.accounts.append(account)

    def remove_accounts(self):
        for btn in self.account_buttons:
            self.delete_component(btn)
        self.account_buttons = []
        self.accounts = None


class AccountCreateScreen(Screen):
    def __init__(self, group: ScreenGroup):
        self.name = Input[str](identity, text="Название:")
        self.amount = Input[float](any_float, text="Сумма:")
        self.save = Button(text="✅ Save", on_change=self.save_handler)
        self.back = Button(text="⬅️ back", on_change=self.back_handler)
        self.account = None
        self.group = group
        super().__init__([self.name, self.amount, self.back, self.save], message="редактирование счета")

    async def get_layout(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> Sequence[
        Sequence[InlineKeyboardButton]]:
        layout = [
            [self.name.render(update, context)],
            [self.amount.render(update, context)]
        ]
        if self.check_form_filled():
            layout += [[self.save.render(update, context)]]
        layout += [[self.back.render(update, context)]]
        return layout

    async def save_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        await create_account(get_user_id(update), self.name.value, self.amount.value)
        await self.group.go_back(update, context)

    async def back_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        await self.group.go_back(update, context)

    def check_form_filled(self) -> bool:
        return self.name.value is not None and self.amount.value is not None


class AccountEditScreen(AccountCreateScreen):
    def __init__(self, account_id: int, group: ScreenGroup):
        self.account_id = account_id
        self.group = group
        self.account: Account | None = None
        self.delete = Button(text="🗑 Delete", on_change=self.delete_handler)
        super().__init__(self.group)
        self.add_components([self.delete])

    async def get_layout(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> Sequence[
        Sequence[InlineKeyboardButton]]:
        await self.init_if_necessary(update, context)
        layout = await super().get_layout(update, context)
        layout += [[]]
        return layout + [[self.delete.render(update, context)]]

    async def init_if_necessary(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if self.account is None:
            user_id = get_user_id(update)
            self.account, balance = await get_user_account_with_balance(user_id, self.account_id)
            self.name.value = self.account.name
            self.amount.value = balance

    async def save_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        self.account.name = self.name.value
        await update_account(get_user_id(update), self.account, self.amount.value)
        await self.group.go_back(update, context)

    async def delete_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        screen = DeleteScreen[int](self.account_id, delete_account_by_id, self.group)
        await self.group.go_to_screen(update, context, screen)


class AccountMain(ScreenGroup):
    description: ClassVar[str] = "счета"

    def __init__(self):
        self.main = AccountsScreen(self)
        super().__init__(self.main)
