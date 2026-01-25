from typing import Sequence

from telegram import InlineKeyboardButton, Update
from telegram.ext import ContextTypes
from tuican import USER_ID
from tuican.components import Button, CheckBox, ExclusiveCheckBoxGroup, Input, Screen, ScreenGroup
from tuican.validation import positive_float

from core.helpers import format_amount
from core.models.account import Account
from core.models.category import Category
from core.models.transaction import Transaction
from core.service.account_service import calculate_account_balance, get_user_accounts
from core.service.category_service import get_user_expense_categories, get_user_income_categories
from core.service.transaction_service import create_transaction, delete_transaction, get_transaction_by_id, \
    update_transaction


def get_account_label(account: Account, amount: float):
    return f'{account.name} ({format_amount(amount)})'


def render_check_boxes(update: Update, context: ContextTypes.DEFAULT_TYPE, check_boxes: list[CheckBox]) -> Sequence[
    Sequence[InlineKeyboardButton]]:
    keyboard = []
    row = []
    for component in check_boxes:
        row.append(component.render(update, context))
        if len(row) == 3:
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

        self.income = CheckBox(text="🟢 Income (+)", component_id="income", selected=True, group=self.type_group)
        self.expense = CheckBox(text="🔴 Expense (-)", component_id="expense", group=self.type_group)
        self.save = Button(text="✅ Save", on_change=self.save_handler)
        self.back = Button(text="⬅️ back", on_change=self.back_handler)

        self.amount = Input[float](positive_float, text="📊Сумма :")

        self.income_categories: list[Category] | None = None
        self.expense_categories: list[Category] | None = None
        self.accounts: list[Account] | None = None

        self.income_checkboxes: list[CheckBox] = []
        self.expense_checkboxes: list[CheckBox] = []
        self.account_checkboxes: list[CheckBox] = []

        self.group = group

        super().__init__([self.income, self.expense, self.amount, self.save, self.back], message="transaction")

    async def get_layout(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> Sequence[
        Sequence[InlineKeyboardButton]]:
        await self.init_if_necessary()
        if self.type_group.get_selected() is None:
            await self.expense.check(update, context, update.callback_query.data)
        income_cb = self.type_group.get_selected() is not None and self.type_group.get_selected().component_id == "income"
        checkboxes = self.income_checkboxes if income_cb else self.expense_checkboxes
        layout = [
            *render_check_boxes(update, context, self.account_checkboxes),
            [self.income.render(update, context), self.expense.render(update, context)],
            *render_check_boxes(update, context, checkboxes),
            [self.amount.render(update, context)],
        ]
        if self.check_form_filled():
            layout += [[self.save.render(update, context)]]
        layout += [[self.back.render(update, context)]]
        return layout

    async def save_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        category = None
        if self.income.selected:
            category = self.income_group.get_selected().text
        if self.expense.selected:
            category = self.expense_group.get_selected().text
        await create_transaction(
            user_id=USER_ID.get(),
            category=category,
            transaction_type=self.type_group.get_selected().component_id,
            account_id=int(self.account_group.get_selected().component_id),
            amount=self.amount.value
        )
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

    async def init_if_necessary(self):
        if self.income_categories is None or self.expense_categories is None or self.accounts is None:
            user_id = USER_ID.get()
            self.income_categories = await get_user_income_categories(user_id)
            self.expense_categories = await get_user_expense_categories(user_id)
            self.accounts = await get_user_accounts(user_id)
            for category in self.income_categories:
                cb = CheckBox(text=category.name, group=self.income_group)
                self.income_checkboxes.append(cb)
                self.add_component(cb)
            for category in self.expense_categories:
                cb = CheckBox(text=category.name, group=self.expense_group)
                self.expense_checkboxes.append(cb)
                self.add_component(cb)
            for account in self.accounts:
                amount = await calculate_account_balance(account.id, user_id)
                cb = CheckBox(text=get_account_label(account, amount), group=self.account_group,
                              component_id=str(account.id))
                self.account_checkboxes.append(cb)
                self.add_component(cb)


class TransactionEdit(TransactionCreate):
    def __init__(self, transaction_id: int, group: ScreenGroup):
        self.transaction_id = transaction_id
        self.transaction: Transaction | None = None
        self.delete = Button(text="🗑 Delete", on_change=self.delete_handler)
        super().__init__(group)
        self.add_components([self.delete])

    async def get_layout(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> Sequence[
        Sequence[InlineKeyboardButton]]:
        await self.init_if_necessary()
        await self.initial_setup(update, context)
        layout = await super().get_layout(update, context)
        layout += [[self.delete.render(update, context)]]
        return layout
    async def save_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        category = None
        if self.income.selected:
            category = self.income_group.get_selected().text
        if self.expense.selected:
            category = self.expense_group.get_selected().text
        await update_transaction(
            transaction_id=self.transaction_id,
            user_id=USER_ID.get(),
            category=category,
            transaction_type=self.type_group.get_selected().component_id,
            account_id=int(self.account_group.get_selected().component_id),
            amount=self.amount.value
        )
        await self.group.go_back(update, context)

    async def delete_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        screen = DeleteScreen(self.transaction_id, self.group)
        await self.group.go_to_screen(update, context, screen)

    async def initial_setup(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if self.transaction is None:
            self.transaction = await get_transaction_by_id(self.transaction_id)
            for account in self.account_checkboxes:
                if account.component_id == str(self.transaction.account_id):
                    await account.check(update, context, update.callback_query.data)
            if self.transaction.type == 'income':
                await self.income.check(update, context, update.callback_query.data)
                for category in self.income_checkboxes:
                    if category.text == self.transaction.category:
                        await category.check(update, context, update.callback_query.data)
            else:
                await self.expense.check(update, context, update.callback_query.data)
                for category in self.expense_checkboxes:
                    if category.text == self.transaction.category:
                        await category.check(update, context, update.callback_query.data)
            self.amount.value = self.transaction.amount

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
        await delete_transaction(self.transaction_id, USER_ID.get())
        await self.group.go_home(update, context)
