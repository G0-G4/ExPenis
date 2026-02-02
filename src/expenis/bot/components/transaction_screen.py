from typing import Sequence

from telegram import InlineKeyboardButton, Update
from telegram.ext import ContextTypes
from tuican import get_user_id
from tuican.components import Button, CheckBox, Component, ExclusiveCheckBoxGroup, Input, Screen, ScreenGroup
from tuican.validation import identity, positive_float

from ...core.helpers import format_amount
from ...core.models.account import Account
from ...core.models.category import Category
from ...core.models import Transaction
from ...core.service import get_user_accounts_with_balance
from ...core.service.category_service import create_default_categories, get_user_categories
from ...core.service.transaction_service import delete_transaction_by_id, get_transaction_by_id, save_transaction, \
    update_transaction


def get_account_label(account: Account, amount: float):
    return f'{account.name} ({format_amount(amount)})'


def render_by_n(update: Update, context: ContextTypes.DEFAULT_TYPE, cmp: list[Component], n: int=3) -> Sequence[
    Sequence[InlineKeyboardButton]]:
    keyboard = []
    row = []
    for component in cmp:
        row.append(component.render(update, context))
        if len(row) == n:
            keyboard.append(row)
            row = []
    if len(row):
        keyboard.append(row)
    return keyboard


class TransactionCreate(Screen):

    def __init__(self, group: ScreenGroup):
        self.income_group = ExclusiveCheckBoxGroup(sticky=True)
        self.expense_group = ExclusiveCheckBoxGroup(sticky=True)
        self.type_group = ExclusiveCheckBoxGroup(sticky=True)
        self.account_group = ExclusiveCheckBoxGroup(sticky=True)

        self.income = CheckBox(text="🟢 Income (+)", component_id="income", group=self.type_group)
        self.expense = CheckBox(text="🔴 Expense (-)", component_id="expense", selected=True, group=self.type_group)
        self.save = Button(text="✅ Save", on_change=self.save_handler)
        self.back = Button(text="⬅️ back", on_change=self.back_handler)

        self.amount = Input[float](positive_float, text="📊Сумма :")
        self.description = Input[str](identity, text="✍️Описание :")

        self.income_categories: list[Category] | None = None
        self.expense_categories: list[Category] | None = None
        self.accounts: list[Account] | None = None

        self.income_checkboxes: list[CheckBox] = []
        self.expense_checkboxes: list[CheckBox] = []
        self.account_checkboxes: list[CheckBox] = []

        self.group = group

        super().__init__([self.income, self.expense, self.amount, self.description, self.save, self.back], message="transaction")

    async def get_layout(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> Sequence[
        Sequence[InlineKeyboardButton]]:
        await self.init_if_necessary(get_user_id(update))
        income_cb = self.type_group.get_selected() is not None and self.type_group.get_selected().component_id == "income"
        checkboxes = self.income_checkboxes if income_cb else self.expense_checkboxes
        saved_account_id = context.user_data.get('account_id', None)
        if saved_account_id is not None and self.account_group.get_selected() is None:
            # TODO get components by id
            for account_cb in self.account_checkboxes:
                if account_cb.data == saved_account_id:
                    await account_cb.check(update, context, update.callback_query.data)
        layout = [
            *render_by_n(update, context, self.account_checkboxes),
            [self.income.render(update, context), self.expense.render(update, context)],
            *render_by_n(update, context, checkboxes),
            [self.amount.render(update, context)],
            [self.description.render(update, context)],
        ]
        if self.check_form_filled():
            layout += [[self.save.render(update, context)]]
        layout += [[self.back.render(update, context)]]
        return layout

    async def save_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        category_id = None
        if self.income.selected:
            category_id = self.income_group.get_selected().component_id
        if self.expense.selected:
            category_id = self.expense_group.get_selected().component_id
        transaction = Transaction(
            user_id=get_user_id(update),
            category=Category(id=int(category_id)),
            transaction_type=self.type_group.get_selected().component_id,
            account=Account(id=self.account_group.get_selected().data),
            amount=self.amount.value,
            description=self.description.value
        )
        await save_transaction(transaction)
        await self.group.go_back(update, context)

    async def back_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        await self.group.go_back(update, context)

    def check_form_filled(self) -> bool:
        return ((self.income.selected and self.income_group.get_selected() is not None or
                 self.expense.selected and self.expense_group.get_selected() is not None) and
                self.type_group.get_selected() is not None and
                self.account_group.get_selected() is not None and
                self.amount.value is not None
                )

    async def init_if_necessary(self, user_id: int):
        if self.income_categories is None or self.expense_categories is None:
            income_categories, expense_categories = await get_user_categories(user_id)
            if not income_categories and not expense_categories:
                await create_default_categories(user_id)
                income_categories, expense_categories = await get_user_categories(user_id)
            self.income_categories = income_categories
            self.expense_categories = expense_categories
            for category in self.income_categories:
                cb = CheckBox(text=category.name, group=self.income_group, component_id=str(category.id))
                self.income_checkboxes.append(cb)
                self.add_component(cb)
            for category in self.expense_categories:
                cb = CheckBox(text=category.name, group=self.expense_group, component_id=str(category.id))
                self.expense_checkboxes.append(cb)
                self.add_component(cb)
        if self.accounts is None :
            accounts_with_balances = await get_user_accounts_with_balance(user_id)
            if len(accounts_with_balances) > 0:
                self.accounts = []
            for account, balance in accounts_with_balances:
                cb = CheckBox(text=get_account_label(account, balance), group=self.account_group, on_change=self.save_account_id)
                cb.data = account.id
                self.account_checkboxes.append(cb)
                self.add_component(cb)
                self.accounts.append(account)

    def save_account_id(self, update: Update, context: ContextTypes.DEFAULT_TYPE, callback_data: str, cmp: Component):
        if isinstance(cmp, CheckBox) and cmp.selected:
            context.user_data['account_id'] = cmp.component_id


class TransactionEdit(TransactionCreate):
    def __init__(self, transaction_id: int, group: ScreenGroup):
        self.transaction_id = transaction_id
        self.transaction: Transaction | None = None
        self.delete = Button(text="🗑 Delete", on_change=self.delete_handler)
        super().__init__(group)
        self.add_components([self.delete])

    async def get_layout(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> Sequence[
        Sequence[InlineKeyboardButton]]:
        await self.initial_setup(update, context)
        layout = await super().get_layout(update, context)
        layout += [[self.delete.render(update, context)]]
        return layout
    async def save_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        category_id = None
        if self.income.selected:
            category_id = self.income_group.get_selected().component_id
        if self.expense.selected:
            category_id = self.expense_group.get_selected().component_id
        transaction = Transaction(
            id=self.transaction_id,
            user_id=get_user_id(update),
            category=Category(id=int(category_id)),
            transaction_type=self.type_group.get_selected().component_id,
            account=Account(id=self.account_group.get_selected().data),
            amount=self.amount.value,
            description=self.description.value
        )
        await update_transaction(transaction)
        await self.group.go_back(update, context)

    async def delete_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        screen = DeleteScreen(self.transaction_id, self.group)
        await self.group.go_to_screen(update, context, screen)

    async def initial_setup(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await super().init_if_necessary(get_user_id(update))
        if self.transaction is None:
            self.transaction = await get_transaction_by_id(self.transaction_id)
            for cb in self.account_checkboxes:
                if cb.data == self.transaction.account_id:
                    await cb.check(update, context, update.callback_query.data)
            if self.transaction.category.type == 'income':
                await self.income.check(update, context, update.callback_query.data)
                for category in self.income_checkboxes:
                    if category.component_id == str(self.transaction.category.id):
                        await category.check(update, context, update.callback_query.data)
            else:
                await self.expense.check(update, context, update.callback_query.data)
                for category in self.expense_checkboxes:
                    if category.component_id == str(self.transaction.category.id):
                        await category.check(update, context, update.callback_query.data)
            self.amount.value = self.transaction.amount
            self.description.value = self.transaction.description

class DeleteScreen(Screen):

    def __init__(self, transaction_id: int, group: ScreenGroup):
        self.group = group
        self.transaction_id = transaction_id
        self.delete = Button(text="🗑 Delete", on_change=self.delete_handler)
        self.cancel = Button(text="❌ Cancel", on_change=self.cancel_handler)
        super().__init__([self.delete, self.cancel], message="Удалить?")

    async def get_layout(self, update, context) -> Sequence[Sequence[InlineKeyboardButton]]:
        return [
            [self.delete.render(update, context), self.cancel.render(update, context)]
        ]

    async def cancel_handler(self,update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        await self.group.go_back(update, context)

    async def delete_handler(self,update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        await delete_transaction_by_id(self.transaction_id)
        await self.group.go_home(update, context)
