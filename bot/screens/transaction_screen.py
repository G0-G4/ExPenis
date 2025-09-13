import asyncio

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, ContextTypes, CallbackQueryHandler
from telegram.error import BadRequest
from typing import Optional

from bot.messages import *
from bot.bot_config import *
from bot.screens.check_box import CheckBox, CheckBoxGroup, Component, Panel, Screen
from core.service.account_service import get_user_accounts, calculate_account_balance
from core.service.category_service import ensure_user_has_categories
from core.helpers import format_amount

class TransactionEdit(Screen):

    def __init__(self, application: Application):
        super().__init__("")
        self.account_selector = AccountSelector(application)
        self.category_selector = CategorySelector(application)


class AccountSelector(Screen): # TODO screen not component

    def __init__(self, application: Application):
        super().__init__(ACCOUNT_SELECTION_MESSAGE)
        self.account_id = None
        self.accounts = []
        self.balance_map = {}
        application.add_handler(CallbackQueryHandler(
            self.handle_user_presses,
            pattern='^cb_|^back$|^enter_transaction$'
        ))

    async def _init(self, user_id, *args, **kwargs):
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
    def account_selection_call_back(self, cbg: CheckBoxGroup):
        if cbg.selected_check_box is not None:
            if cbg.selected_check_box.selected:
                self.account_id = int(cbg.selected_check_box.component_id.split("_")[1])
            else:
                self.account_id = None
        print("account set to " + str(self.account_id))

    async def handle_user_presses(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        user_id = query.from_user.id
        initiated = self.initiated
        if not self.initiated:
            await self._init(user_id)
            self.initiated = True
        if not initiated or await self.panel.handle_callback(query.data):
            await self.display_on(
                update,
                self.message,
                self.panel
            )




class CategorySelector(Screen):

    def __init__(self, application: Application, transaction_type='expense'):
        super().__init__(INCOME_CATEGORY_MESSAGE)
        self.income_cats = []
        self.expense_cats = []
        self.transaction_type = transaction_type
        self.category = None
        self.panel = None
        self.category_map = {}
        self.initiated = False
        application.add_handler(CallbackQueryHandler(
            self.handle_user_presses,
            pattern='^cb_|^back$|^enter_transaction$'
        ))
    async def _init(self, user_id: int, update: Update, transaction_type='expense'):
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

    async def _handle_type_change(self, cbg: CheckBoxGroup, update: Update):
        if cbg.selected_check_box is not None:
            if cbg.selected_check_box.selected:
                self.transaction_type = cbg.selected_check_box.component_id
                user_id  = update.callback_query.from_user.id
                await self._init(user_id, update, self.transaction_type)
                await self.display_on(update, ACCOUNT_SELECTION_MESSAGE, self.panel) # TODO
            else:
                self.transaction_type= None
        print("type set to " + str(self.transaction_type))

    def _handle_category_change(self, cbg: CheckBoxGroup):
        if cbg.selected_check_box is not None:
            if cbg.selected_check_box.selected:
                category_id = int(cbg.selected_check_box.component_id.split("_")[1])
                self.category = self.category_map[category_id].name
            else:
                self.category = None
        print("category set " + self.category)

    async def handle_user_presses(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        user_id = query.from_user.id
        initiated = self.initiated
        if not self.initiated:
            await self._init(user_id, update=update)
            self.initiated = True
        if not initiated or await self.panel.handle_callback(query.data):
            await self.display_on(
                update,
                self.message,
                self.panel
            )
